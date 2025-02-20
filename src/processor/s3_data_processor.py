"""Lambda - to process s3 data and insert into DynamoDB table."""

import json
import boto3
import decimal
import logging
import os
from botocore.exceptions import BotoCoreError, ClientError


def is_running_in_lambda():
    """Return environment."""
    return "AWS_LAMBDA_FUNCTION_NAME" in os.environ


# Moto for local testing only
if not is_running_in_lambda():
    from moto import mock_aws

    mock_aws().start()
    boto3.setup_default_session()

# Hardcoded values for now
S3_BUCKET_NAME = "project-data-pipeline-data-bucket"
DYNAMODB_TABLE_NAME = "project-data-pipeline-table"

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
s3_client = boto3.client("s3", region_name="us-east-1")

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def process_s3_event(bucket_name, object_key):
    """Process an S3 event by reading JSON data and storing it in DynamoDB."""
    try:
        logging.info(f"Processing file {object_key} from bucket {bucket_name}")

        file_content = read_s3_file(bucket_name, object_key)
        if file_content:
            for single_record in file_content:
                store_in_dynamodb(single_record, object_key)

    except Exception as e:
        logging.error(f"Failed to process S3 file {object_key}: {e}")


def lambda_handler(event, context):
    """AWS Lambda entry point triggered by S3 events."""
    try:
        for record in event["Records"]:
            bucket_name = record["s3"]["bucket"]["name"]
            object_key = record["s3"]["object"]["key"]
            process_s3_event(bucket_name, object_key)

    except KeyError as e:
        logging.error(f"Event format error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


def read_s3_file(bucket, object_key):
    """Retrieve a JSON file from S3 and return the parsed content."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=object_key)
        file_content = response["Body"].read().decode("utf-8")
        return json.loads(file_content)
    except s3_client.exceptions.NoSuchKey:
        logging.error(f"Failed to read S3 file {object_key}: No such key exists.")
    except Exception as e:
        logging.error(f"Failed to read file {object_key} from S3: {e}")
    return None


def store_in_dynamodb(record, file_name):
    """Insert a single JSON record into DynamoDB."""
    try:
        table = dynamodb.Table(
            DYNAMODB_TABLE_NAME
        )  # Ensure table reference is inside function scope
        formatted_data = {
            "site_id": record["site_id"],
            "timestamp": record["timestamp"],
            "energy_generated_kwh": decimal.Decimal(
                str(record["energy_generated_kwh"])
            ),
            "energy_consumed_kwh": decimal.Decimal(str(record["energy_consumed_kwh"])),
            "net_energy_kwh": decimal.Decimal(
                str(
                    round(
                        record["energy_generated_kwh"] - record["energy_consumed_kwh"],
                        2,
                    )
                )
            ),
            "anomaly": bool(
                record["energy_generated_kwh"] < 0 or record["energy_consumed_kwh"] < 0
            ),
        }

        table.put_item(Item=formatted_data)
        logging.info(f"Successfully stored record from {file_name} into DynamoDB.")

    except (BotoCoreError, ClientError) as e:
        logging.error(f"Failed to store data in DynamoDB for {file_name}: {e}")
