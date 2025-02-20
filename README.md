# Energy Data Pipeline

This project simulates energy data, stores it locally or uploads it to AWS S3, and processes it for storage in DynamoDB.

## Features
- **DataSimulator**: Continuously generates energy data and stores it locally or uploads it to S3.
- **S3 Data Processor**: Processes S3 data and inserts records into DynamoDB.

## Prerequisites
1. Python 3.13 (tested) or Python 3.10+ (for broader compatibility)
2. IAM User credentials, AWS Account ID

## Setup Instructions

1. Clone the repository - `git clone <https://github.com/ambreashwini/DataPipeline.git>`
2. Change directory - `cd DataPipeline`
3. Create a virtual environment (optional but recommended) -
   `python3 -m venv .venv
    source .venv/bin/activate`
4. Install dependencies - `pip install -r requirements.txt`
5. Configure AWS Credentials - https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html
6. Set up your environment variables:
   1. Create a `.env` file at the root of the project and add the following:
      `ENVIRONMENT=LOCAL`
   2. Create a `aws_credentials.yml` and add your credentials as below:
      `{
        "aws_access_key_id":"<AWS USER ACCESS KEY ID>",
        "aws_secret_access_key":"<AWS USER SECRET>"
      }`
7. Once ready, run setup - `python3 setup.py`
8. Once setup is successful move on to deployment steps

## AWS CLI Commands for deployment (after setup.py, WIP)
1. Check AWS Credentials `aws sts get-caller-identity --profile data-pipeline-local-profile`
2. If you don't see, reconfigure `aws configure --profile data-pipeline-local-profile`
3. Create IAM Role for Lambda
`aws iam create-role \
    --role-name project-data-pipeline-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": { "Service": "lambda.amazonaws.com" },
            "Action": "sts:AssumeRole"
        }]
    }'`
4. Attach Policies for S3, DynamoDB, and Log
`aws iam put-role-policy \
    --role-name project-data-pipeline-role \
    --policy-name project-data-pipeline-policy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": [
                    "arn:aws:s3:::project-data-pipeline-data-bucket/*",
                    "arn:aws:s3:::project-data-pipeline-code-bucket/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": ["dynamodb:PutItem", "dynamodb:BatchWriteItem"],
                "Resource": "arn:aws:dynamodb:us-east-1:<ACCOUNT_ID>:table/project-data-pipeline-table"
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": "arn:aws:logs:us-east-1:<ACCOUNT_ID>:*"
            }
        ]
    }'`
5. Create S3 Bucket for lambda code
`aws s3api create-bucket --bucket project-data-pipeline-code-bucket --region us-east-1`
6. Create S3 Bucket for data
`aws s3api create-bucket --bucket project-data-pipeline-data-bucket --region us-east-1`
7. Create DynamoDB Table
`aws dynamodb create-table \
    --table-name project-data-pipeline-table \
    --attribute-definitions AttributeName=site_id,AttributeType=S AttributeName=timestamp,AttributeType=N \
    --key-schema AttributeName=site_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST`
8. Simulator Lambda - package, upload to s3 and clean up
`mkdir -p simulator_package
pip install -r requirements.txt -t simulator_package/
cp src/simulator/data_simulator.py simulator_package/
cd simulator_package && zip -r ../simulator_lambda.zip . && cd ..
aws s3 cp simulator_lambda.zip s3://project-data-pipeline-code-bucket/
rm -rf simulator_package simulator_lambda.zip`
9. Deploy Simulator Lambda function
`aws lambda create-function \
    --function-name project-data-pipeline-simulator \
    --runtime python3.12 \
    --role arn:aws:iam::<ACCOUNT_ID>:role/project-data-pipeline-role \
    --handler data_simulator.lambda_handler \
    --timeout 300 \
    --memory-size 128 \
    --code S3Bucket=project-data-pipeline-code-bucket,S3Key=simulator_lambda.zip`
10. Processor Lambda - package, upload to s3 and clean up
`mkdir -p processor_package
pip install -r requirements.txt -t processor_package/
cp src/processor/s3_data_processor.py processor_package/
cd processor_package && zip -r ../processor_lambda.zip . && cd ..
aws s3 cp processor_lambda.zip s3://project-data-pipeline-code-bucket/
rm -rf processor_package processor_lambda.zip`
11. Deploy Processor Lambda function
`aws lambda create-function \
    --function-name project-data-pipeline-processor \
    --runtime python3.12 \
    --role arn:aws:iam::<ACCOUNT_ID>:role/project-data-pipeline-role \
    --handler s3_data_processor.lambda_handler \
    --code S3Bucket=project-data-pipeline-code-bucket,S3Key=processor_lambda.zip`
12. Create EventBridge Rule to invoke Simulator Lambda function every 5 Minutes
`aws events put-rule \
    --name invoke-simulator-every-five-mins \
    --schedule-expression "rate(5 minutes)"`
13. Grant EventBridge permissions to invoke Simulator Lambda
`aws lambda add-permission \
    --function-name project-data-pipeline-simulator \
    --statement-id event-bridge-invoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:us-east-1:<ACCOUNT_ID>:rule/invoke-simulator-every-five-mins`
14. Attach Simulator Lambda as the target to EventBridge rule
`aws events put-targets \
    --rule invoke-simulator-every-five-mins \
    --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:project-data-pipeline-simulator"
`
15. Grant S3 Permission to invoke Processor Lambda
`aws lambda add-permission \
    --function-name project-data-pipeline-processor \
    --statement-id s3invoke \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::project-data-pipeline-data-bucket \
    --source-account <ACCOUNT_ID>`
16. Configure S3 Event Notification to Trigger Processor Lambda
`aws s3api put-bucket-notification-configuration \
    --bucket project-data-pipeline-data-bucket \
    --notification-configuration '{
        "LambdaFunctionConfigurations": [
            {
                "LambdaFunctionArn": "arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:project-data-pipeline-processor",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {"Name": "suffix", "Value": ".json"}
                        ]
                    }
                }
            }
        ]
    }'`

# Verification of infrastructure deployment:
1. List functions - `aws lambda list-functions | grep project-data-pipeline`
2. List buckets - `aws s3 ls `
3. List bucket contents - `aws s3 ls s3://project-data-pipeline-data-bucket/`
4. List tables - `aws dynamodb list-tables`
5. List events - `aws events list-rules | grep invoke-simulator`
6. Verify Processor Lambda Execution -
`aws lambda invoke \
    --function-name project-data-pipeline-processor \
    --payload '{"test": "data"}' \
    response.json
cat response.json`
7. Verify Data in DynamoDB Table - `aws dynamodb scan --table-name project-data-pipeline-table`


## To-Do
- Handle scalability - batch write to DynamoDB (currently single item )
- Visualizing the processed data
- API to query data
- Automated deployment using Terraform
- 