import json
import os
import random
import time
import signal
import sys
import yaml
import logging
from datetime import datetime, UTC
from utils.s3_utils import S3Utils

# Load Configuration
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

LOCAL_CONFIG = config["local"]
S3_CONFIG = config["s3_config"]
TIMESTAMP_FORMAT = config["global"]["timestamp_format"]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def generate_data():
    """
    Generate a single energy data record
    """
    site_number = random.randint(1, 100)
    site_id = f'SITECA{site_number:03d}'

    return {
        'site_id': site_id,
        'timestamp': datetime.now(UTC).strftime(TIMESTAMP_FORMAT),
        'energy_generated_kwh': round(random.uniform(10, 200), 2),
        'energy_consumed_kwh': round(random.uniform(5, 180), 2)
    }


class DataSimulator:
    """
    - Simulate energy data
    - Store locally or upload to S3 based on user choice
    """

    def __init__(self, local_enabled=True, s3_enabled=False):
        """
        Initialize the simulator based on configuration
        """
        self.local_enabled = local_enabled
        self.s3_enabled = s3_enabled
        self.local_data_path = os.path.abspath(LOCAL_CONFIG["data_path"])
        self.stop_signal = False
        self.data_feed = []

        if self.local_enabled:
            os.makedirs(self.local_data_path, exist_ok=True)
            logging.info(f"Local data path: {self.local_data_path}")

        signal.signal(signal.SIGINT, self.signal_handler)
        logging.info("DataSimulator initialized successfully.")

        self.s3_utils = S3Utils(bucket_name=S3_CONFIG["bucket_name"]) if self.s3_enabled else None

    def signal_handler(self, sig, frame):
        """
        Handle termination signal, if interrupted
        """
        self.stop_signal = True
        sys.stdout.flush()

    def save_data_locally(self):
        """
        Save collected data to local folder (only for local testing)
        """
        if not self.data_feed:
            logging.info("Interrupted before next data interval. No new data to save.")
            return

        timestamp = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
        file_path = os.path.join(self.local_data_path, f"{timestamp}_data.json")

        with open(file_path, 'w') as f:
            json.dump(self.data_feed, f, indent=4)

        logging.info(f"Data successfully saved locally at {file_path}")

    def upload_data_to_s3(self):
        """
        Upload collected data to S3 if enabled
        """
        if not self.data_feed or not self.s3_utils:
            logging.info("No data to upload OR S3 is not enabled.")
            return

        timestamp = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
        s3_key = f"{timestamp}_data.json"

        if self.s3_utils.upload_json_data(self.data_feed, s3_key):
            logging.info(f"Successfully uploaded data feed to S3: {s3_key}")

    def simulate_data(self, data_interval=5, file_interval=20):
        """
        Continuously generate and store data to local/s3.
        """
        start_time = time.time()
        last_data_time = start_time

        while not self.stop_signal:
            current_time = time.time()

            if current_time - last_data_time >= data_interval:
                self.data_feed.append(generate_data())
                last_data_time = current_time

            if current_time - start_time >= file_interval:
                self._store_data()
                start_time = time.time()

            time.sleep(0.5)

        self._store_data()
        logging.info("Final data saved and uploaded. Exiting gracefully.")

    def _store_data(self):
        """
        store data locally or in S3
        """
        if self.local_enabled:
            self.save_data_locally()
        if self.s3_enabled:
            self.upload_data_to_s3()

        self.data_feed = []


def main():
    """
    entry point the data simulator
    """
    print("\nPlease select one mode:")
    print("1. Local (Local file simulation only)")
    print("2. S3 (Simulate data and upload to DynamoDB)")

    while True:
        choice = input("\nEnter 1 for Local or 2 for S3: ").strip()
        if choice in ["1", "2"]:
            break
        print("Invalid selection. Please enter 1 or 2.")

    local_enabled = choice == "1"
    s3_enabled = choice == "2"

    if s3_enabled:
        bucket_name = input(f"Enter S3 bucket name [{S3_CONFIG['bucket_name']}]: ") or S3_CONFIG['bucket_name']
        S3_CONFIG["bucket_name"] = bucket_name
        logging.info(f"S3 data simulation enabled with bucket [{S3_CONFIG['bucket_name']}]")
    else:
        logging.info(f"Local simulation enabled. Data will be saved at - {LOCAL_CONFIG['data_path']}")

    simulator = DataSimulator(
        local_enabled=local_enabled,
        s3_enabled=s3_enabled
    )

    simulator.simulate_data(data_interval=3, file_interval=60)


if __name__ == "__main__":
    main()
