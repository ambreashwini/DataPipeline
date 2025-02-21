"""Lambda - to generate energy data as JSON files and upload them to S3 bucket."""

import json
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


def is_running_in_lambda():
    """Check if running in AWS Lambda environment."""
    try:
        boto3.client("sts").get_caller_identity()  # AWS check
        return "AWS_LAMBDA_FUNCTION_NAME" in os.environ
    except:
        return False


# Keep Moto for local testing only
if not is_running_in_lambda():
    from moto import mock_aws

# Load environment variables
load_dotenv()
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"
AWS_BUCKET_NAME = "project-data-pipeline-data-bucket"

# Define environment (AWS or Local)
ENVIRONMENT = os.getenv("ENVIRONMENT", "AWS").upper()
USE_MOCK = ENVIRONMENT == "LOCAL"  # Use mock S3 for local testing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class S3Utils:
    """Upload data to s3 bucket."""

    def __init__(self, bucket_name=AWS_BUCKET_NAME, mock=USE_MOCK):
        """Initialize S3 client. Uses mock S3 in test mode."""
        self.bucket_name = bucket_name
        self.mock = mock

        if self.mock:
            logging.info("Using Moto mock S3 (no credentials required).")
            self.mock_s3 = mock_aws()
            self.mock_s3.start()
            self.s3_client = boto3.client("s3", region_name="us-east-1")
            self._create_mock_bucket()
        else:
            logging.info("Running in AWS environment.")
            self.s3_client = boto3.client("s3")  # Use IAM role, no profile

        logging.info(
            f"S3Utils initialized for bucket: {self.bucket_name} (mock={self.mock})"
        )

    def _create_mock_bucket(self):
        """Ensure the S3 bucket is created when running locally in mock mode."""
        try:
            self.s3_client.create_bucket(Bucket=self.bucket_name)
            logging.info(f"Mock S3 bucket '{self.bucket_name}' created successfully.")
        except self.s3_client.exceptions.BucketAlreadyOwnedByYou:
            logging.info(f"Mock S3 bucket '{self.bucket_name}' already exists.")
        except Exception as e:
            logging.error(f"Error creating mock S3 bucket: {e}")

    def upload_json_data(self, data, s3_key):
        """Upload data to S3 or mock S3 in test mode."""
        try:
            json_data = json.dumps(data, indent=4)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data,
                ContentType="application/json",
            )
            logging.info(f"Uploaded JSON data to s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logging.error(f"Failed to upload JSON data to S3: {e}")
            return False

    def stop_mock(self):
        """Stop the Moto mock when the simulator exits."""
        if self.mock:
            self.mock_s3.stop()


class DataSimulator:
    """To generate and store energy data in s3 bucket."""

    def __init__(self, mock=USE_MOCK):
        """Initialize the data simulator with S3Utils."""
        self.mock = mock
        self.stop_signal = False
        self.data_feed = []
        self.s3_utils = S3Utils(bucket_name=AWS_BUCKET_NAME, mock=self.mock)

        signal.signal(signal.SIGINT, self._signal_handler)
        logging.info(f"DataSimulator initialized successfully (mock={self.mock}).")

    def _signal_handler(self, sig, frame):
        """Gracefully handle termination signals."""
        self.stop_signal = True
        sys.stdout.flush()

    def _store_data(self):
        """Upload data to S3."""
        if not self.data_feed:
            logging.info("No new data to save.")
            return

        timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
        file_name = f"{timestamp}_data.json"

        logging.info("Saving data to S3 bucket")
        self.s3_utils.upload_json_data(self.data_feed, file_name)
        logging.info(f"Uploaded data to S3: {file_name}")
        self.data_feed = []

    def generate_data(self):
        """Generate random energy generation and consumption data."""
        site_number = random.randint(1, 100)
        site_id = f"SITECA{site_number:03d}"
        energy_generated = round(random.uniform(10, 200), 2)
        energy_consumed = round(random.uniform(5, 180), 2)

        if random.random() < 0.1:
            energy_generated = round(random.uniform(-2, 0), 2)
        if random.random() < 0.1:
            energy_consumed = round(random.uniform(-2, 0), 2)

        return {
            "site_id": site_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "energy_generated_kwh": energy_generated,
            "energy_consumed_kwh": energy_consumed,
        }

    def simulate_data(self, data_interval=20, context=None):
        """Generate energy data every `data_interval` seconds and upload a single file before Lambda exits."""
        self.data_feed = []
        logging.info("Simulation started.")

        start_time = time.time()

        while True:
            if context:
                remaining_time = context.get_remaining_time_in_millis() / 1000
            else:
                remaining_time = 300 - (time.time() - start_time)

            if remaining_time < 15:  # Stop early to ensure data is saved
                logging.info("Approaching timeout. Uploading data and exiting.")
                break

            data = self.generate_data()
            logging.info(f"Generated data: {data}")
            self.data_feed.append(data)

            time.sleep(data_interval)

        self._store_data()
        logging.info("Lambda execution complete.")


def main(event=None, context=None, mock=USE_MOCK):
    """Entry point for lambda execution."""
    simulator = DataSimulator(mock=mock)
    simulator.simulate_data(data_interval=20)


if __name__ == "__main__":
    main()


def lambda_handler(event, context):
    """AWS Lambda entry point."""
    logging.info("Lambda function started.")
    main(event, context, mock=False)
    return {
        "statusCode": 200,
        "body": json.dumps("Simulator Lambda executed successfully."),
    }
