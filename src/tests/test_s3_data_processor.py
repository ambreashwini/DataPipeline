"""Tests for s3 data processor Lambda."""

import json
import boto3
import pytest
from moto import mock_aws
from src.processor.s3_data_processor import lambda_handler, process_s3_event


@pytest.fixture(scope="function")
def setup_mock_aws():
    """Set up mock S3 and DynamoDB for testing."""
    with mock_aws():
        boto3.setup_default_session()

        # Initialize mock S3
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "test-bucket"
        s3_client.create_bucket(Bucket=bucket_name)

        # Initialize mock DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table_name = "project-data-pipeline-table"

        # Ensure previous test runs don’t cause conflicts
        existing_tables = dynamodb.meta.client.list_tables()["TableNames"]
        if table_name in existing_tables:
            dynamodb.Table(table_name).delete()
            dynamodb.meta.client.get_waiter("table_not_exists").wait(
                TableName=table_name
            )

        # Create the DynamoDB table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "site_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "site_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Wait for table creation
        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)

        yield s3_client, dynamodb, bucket_name, table_name


def test_process_s3_event(setup_mock_aws):
    """Test processing of an S3 event."""
    s3_client, dynamodb, bucket_name, table_name = setup_mock_aws

    # Upload test data to S3
    test_data = [
        {
            "site_id": "SITE001",
            "timestamp": 1708400000,
            "energy_generated_kwh": 120,
            "energy_consumed_kwh": 90,
        },
        {
            "site_id": "SITE002",
            "timestamp": 1708400010,
            "energy_generated_kwh": 150,
            "energy_consumed_kwh": 110,
        },
    ]
    file_key = "test_data.json"
    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=json.dumps(test_data))

    # Validate file existence in S3
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    assert "Contents" in response, "S3 object was not uploaded!"
    assert any(
        obj["Key"] == file_key for obj in response["Contents"]
    ), "Test file not found in S3!"

    # Process event
    process_s3_event(bucket_name, file_key)

    # Verify data insertion in DynamoDB
    table = dynamodb.Table(table_name)
    response = table.scan()
    items = response["Items"]

    assert len(items) == 2, f"Expected 2 records, found {len(items)}"


def test_lambda_handler(setup_mock_aws):
    """Test Lambda execution."""
    s3_client, dynamodb, bucket_name, table_name = setup_mock_aws

    # Upload test file
    test_data = [
        {
            "site_id": "SITE001",
            "timestamp": 1708400000,
            "energy_generated_kwh": 120,
            "energy_consumed_kwh": 90,
        }
    ]
    file_key = "event_data.json"
    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=json.dumps(test_data))

    # Validate S3 object exists
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    assert any(
        obj["Key"] == file_key for obj in response.get("Contents", [])
    ), "S3 event file is missing!"

    # Simulate S3 event
    test_event = {
        "Records": [
            {"s3": {"bucket": {"name": bucket_name}, "object": {"key": file_key}}}
        ]
    }

    # Execute Lambda
    lambda_handler(test_event, None)

    # Verify data in DynamoDB
    table = dynamodb.Table(table_name)
    response = table.scan()
    items = response["Items"]

    assert len(items) == 1, f"Expected 1 record, found {len(items)}"
    assert items[0]["site_id"] == "SITE001"
