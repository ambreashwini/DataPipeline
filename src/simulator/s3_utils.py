import json
import logging

import boto3
import yaml
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError

# Load Configuration from config
with open("simulator/config.yaml", "r") as f:
    config = yaml.safe_load(f)

S3_BUCKET_NAME = config["s3_config"]["bucket_name"]
AWS_PROFILE_NAME = "aws-ui-profile-test"  # Set the profile you need to use

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class S3Utils:
    """
    S3 Utils - to handle S3 operations
    """

    def __init__(self, bucket_name=S3_BUCKET_NAME):
        """Initialize the S3 client using the specified AWS profile"""
        self.bucket_name = bucket_name

        try:
            session = boto3.Session(profile_name=AWS_PROFILE_NAME)
            self.s3_client = session.client('s3')
            logging.info(f"S3Utils initialized for bucket: {self.bucket_name} using profile: {AWS_PROFILE_NAME}")
            self.validate_aws_credentials()
        except NoCredentialsError:
            logging.error("AWS credentials not found. Ensure they are configured correctly.")
            raise
        except BotoCoreError as e:
            logging.error(f"Error initializing S3 client: {e}")
            raise

    def validate_aws_credentials(self):
        """
        Validate AWS credentials to see if bucket is accessible
        """
        try:
            self.s3_client.list_buckets()
            logging.info("AWS credentials validated successfully.")
        except NoCredentialsError:
            logging.error("Invalid AWS credentials. Please configure them correctly.")
            raise
        except BotoCoreError as e:
            logging.error(f"Error validating AWS credentials: {e}")
            raise

    def upload_json_data(self, data, s3_key):
        """ Upload a JSON object to S3 bucket"""
        try:
            json_data = json.dumps(data, indent=4)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data,
                ContentType="application/json"
            )
            logging.info(f"Uploaded JSON data feed s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logging.error(f"Failed to upload JSON data to S3: {e}")
            return False
