import boto3
import json
import decimal
import logging
import yaml
from botocore.exceptions import BotoCoreError, ClientError

# Load Configuration
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

S3_BUCKET_NAME = config["s3_config"]["bucket_name"]
DYNAMODB_TABLE_NAME = config["s3_config"]["dynamodb_table"]
TIMESTAMP_FORMAT = config["global"]["timestamp_format"]

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

s3_client = boto3.client('s3')

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_s3_event(bucket_name, object_key):
    """
    Process a single S3 event:
    - Reads a JSON file from S3
    - Processes each record one at a time
    - Stores it in DynamoDB
    """
    try:
        logging.info(f"Processing file {object_key} from bucket {bucket_name}")

        file_content = read_s3_file(bucket_name, object_key)
        if file_content:
            for single_record in file_content:  # Process each record individually
                store_in_dynamodb(single_record, object_key)

    except Exception as e:
        logging.error(f"Failed to process S3 file {object_key}: {e}")


def lambda_handler(event, context):
    """
    Lambda function triggered by an S3 event.
    Iterates over records and calls process_s3_event().
    """
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
    """
    Load JSON file from S3 bucket.
    """
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
    """
    Store a single JSON record into DynamoDB.
    """
    # TODO - upate to round up or limit decimal places if necessary
    # net_energy_kwh
    # -22.560000000000002
    try:
        formatted_data = {
            "site_id": record["site_id"],
            "timestamp": record["timestamp"],
            "energy_generated_kwh": decimal.Decimal(str(record["energy_generated_kwh"])),
            "energy_consumed_kwh": decimal.Decimal(str(record["energy_consumed_kwh"])),
            "net_energy_kwh": decimal.Decimal(str(record["energy_generated_kwh"] - record["energy_consumed_kwh"])),
            "anomaly": record["energy_generated_kwh"] < 0 or record["energy_consumed_kwh"] < 0
        }

        table.put_item(Item=formatted_data)  # Inserts a single record
        logging.info(f"Successfully stored record from {file_name} into DynamoDB.")

    except (BotoCoreError, ClientError) as e:
        logging.error(f"Failed to store data in DynamoDB for {file_name}: {e}")
