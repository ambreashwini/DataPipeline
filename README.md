# Energy Data Pipeline

This project simulates energy data, stores it locally or uploads it to AWS S3, and processes it for storage in DynamoDB.

## Features
- **DataSimulator**: Continuously generates energy data and stores it locally or uploads it to S3.
- **S3Utils**: Handles AWS credentials validation and uploads data to S3.
- **S3 Data Processor**: Processes S3 data and inserts records into DynamoDB.

## Prerequisites
1. Python 3.13 (tested) or Python 3.10+ (for broader compatibility)
2. S3 Bucket: `energy-data-feed-dev` for storing data files.
3. Lambda Function: `s3_data_processor` to process S3 events.
4. DynamoDB Table: `SiteEnergyFeed` for storing processed records with partition key - `site_id (String)` and sort key - `timestamp (String)`
5. IAM roles: `s3_data_processor-role-<actual_value>` for lambda function
6. IAM User and permissions: Necessary permissions are granted for S3, Lambda, and DynamoDB access to IAM user

## Setup Instructions

1. Clone the repository - `git clone <https://github.com/ambreashwini/DataPipeline.git>`
2. Change directory - `cd DataPipeline`
3. Create a virtual environment (optional but recommended) - 
   `python -m venv .venv
    source .venv/bin/activate`
4. Install dependencies - `pip install -r requirements.txt`
5. Configure AWS Credentials - https://docs.aws.amazon.com/cli/v1/userguide/cli-chap-configure.html
6. Run the Data Simulator - `python src/data_simulator.py`
7. When prompted, select '2' to enable S3 file upload.
8. To stop - `ctrl+c`

## To-Do
- Add test cases for testing
- Add error handling and retries for S3 operations
- Expand configuration options
- Handle scalability - multiple sites, batch write to DynamoDB
- Terraform or AWS CLI scripts to deploy the infrastructure (S3, DynamoDB, Lambda, IAM roles, and event triggers)
- API endpoints for querying the DynamoDB table
- Visualizing the processed data