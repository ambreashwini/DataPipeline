"""Tests for data simulator Lambda."""

import pytest
import boto3
import json
import os
import signal
import time
from moto import mock_aws
from src.simulator.data_simulator import DataSimulator, AWS_BUCKET_NAME

# Dummy AWS credentials for testing
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_SESSION_TOKEN"] = "test"


@pytest.fixture
@mock_aws
def simulator_mock():
    """Create a DataSimulator instance with Moto mocking S3."""
    s3_client = boto3.client("s3", region_name="us-east-1")
    # Create a dummy bucket
    s3_client.create_bucket(Bucket=AWS_BUCKET_NAME)
    return DataSimulator(mock=True)


def test_data_generation(simulator_mock):
    """Check if `generate_data()` returns valid JSON data."""
    data = simulator_mock.generate_data()

    assert isinstance(data, dict)
    assert "site_id" in data
    assert "timestamp" in data
    assert "energy_generated_kwh" in data
    assert "energy_consumed_kwh" in data
    assert isinstance(data["energy_generated_kwh"], float)
    assert isinstance(data["energy_consumed_kwh"], float)


def test_data_upload(simulator_mock):
    """Check if `_store_data()` uploads data to s3 bucket correctly."""
    simulator_mock.data_feed.append(simulator_mock.generate_data())
    simulator_mock._store_data()

    # Check S3 for uploaded data
    s3_client = simulator_mock.s3_utils.s3_client
    response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME)

    assert "Contents" in response  # Making sure data was generated
    assert len(response["Contents"]) > 0  # At least one file should be there


def test_mock_s3_bucket_exists(simulator_mock):
    """Check if the dummy S3 bucket is created."""
    s3_client = simulator_mock.s3_utils.s3_client
    response = s3_client.list_buckets()

    bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
    assert AWS_BUCKET_NAME in bucket_names  # Making sure bucket was created


def test_simulator_handles_sigint(simulator_mock):
    """Test if the simulator correctly handles SIGINT."""
    import threading

    def run_simulator():
        simulator_mock.simulate_data(data_interval=5)

    simulator_thread = threading.Thread(target=run_simulator)
    simulator_thread.start()

    # delay before sigint
    time.sleep(1)
    signal.raise_signal(signal.SIGINT)

    # time for clean up
    simulator_thread.join()

    assert simulator_mock.stop_signal is True  # test if SIGINT was caught
