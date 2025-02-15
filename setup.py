import os
import logging
import subprocess
import json
import sys

# Reset logging
logging.getLogger().handlers.clear()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)


def setup_interrupted():
    """Handle setup interruption gracefully."""
    logging.info("\nProcess interrupted, setup incomplete. Please rerun.")
    sys.stdout.flush()
    sys.exit(1)


def check_virtual_env():
    # checking virtual env
    if sys.prefix == sys.base_prefix:
        logging.error("Virtual environment is not active. Please activate venv before running this script.")
        sys.exit(1)
    logging.info("Virtual environment is active.")


def check_aws_cli():
    # checking if aws cli is installed
    if subprocess.run(["aws", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        logging.info("AWS CLI installed.")
    else:
        logging.warning("AWS CLI is not installed. Installing now...")
        if subprocess.run(["pip", "install", "awscli"]).returncode != 0:
            logging.error("Failed to install AWS CLI. Please install it manually.")
            sys.exit(1)


def list_aws_profiles():
    # checking existing profiles
    try:
        result = subprocess.run(["aws", "configure", "list-profiles"], capture_output=True, text=True, check=True)
        return [p.strip() for p in result.stdout.split("\n") if p.strip()]
    except subprocess.CalledProcessError:
        return []


def validate_profile(profile):
    # validating input credentials
    try:
        logging.info(f"Validating credentials for profile '{profile}'")
        result = subprocess.run(["aws", "sts", "get-caller-identity", "--profile", profile], capture_output=True,
                                text=True, check=True)
        json_data = json.loads(result.stdout)
        return "Account" in json_data
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        logging.error(f"Invalid credentials for profile '{profile}'. Please check and retry.")
        return False


def setup_new_profile(existing_profiles):
    # set up aws profile locally
    if existing_profiles:
        logging.info(f"Existing profiles: {', '.join(existing_profiles)}")
        logging.info("Please enter a profile name that is NOT in the above list.")
    else:
        logging.info("No existing profiles detected. Please enter a name for your AWS profile.")

    sys.stdout.flush()

    while True:
        try:
            profile = input("Enter AWS profile name: ").strip()
            if profile not in existing_profiles:
                break
            logging.warning(f"Profile '{profile}' already exists. Choose a different name.")
        except KeyboardInterrupt:
            setup_interrupted()

    logging.info("profile name accepted, enter AWS credentials -")
    sys.stdout.flush()

    while True:
        try:
            aws_access_key = input("AWS Access Key ID: ").strip()
            aws_secret_key = input("AWS Secret Access Key: ").strip()
            aws_region = input("AWS region [default: us-east-1]: ").strip() or "us-east-1"

            for key, value in [("aws_access_key_id", aws_access_key), ("aws_secret_access_key", aws_secret_key),
                               ("region", aws_region)]:
                subprocess.run(["aws", "configure", "set", key, value, "--profile", profile])

            if validate_profile(profile):
                break
            else:
                logging.warning("Invalid credentials provided. Please re-enter valid AWS credentials.")
        except KeyboardInterrupt:
            setup_interrupted()

    logging.info(f"AWS profile '{profile}' configured successfully. Using this profile.")
    return assume_role(profile)


def assume_role(profile):
    """Extract IAM role and assume it."""
    sys.stdout.flush()

    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--profile", profile],
            capture_output=True, text=True, check=True
        )
        identity = json.loads(result.stdout)
        arn = identity.get("Arn", "")
        user_name = arn.split("/")[-1] if arn else "Unknown"
        logging.info(f"Checking IAM username for {profile} profile")
        logging.info(f"Finished setup - Profile: {profile}, IAM role: {user_name}")

        return profile
    except subprocess.CalledProcessError:
        logging.error("Error fetching AWS account ID.")
        return profile


if __name__ == "__main__":
    try:
        logging.info("Checking virtual environment and AWS setup")
        sys.stdout.flush()
        check_virtual_env()
        check_aws_cli()
        profiles = list_aws_profiles()
        profile = setup_new_profile(profiles)

        sys.stdout.flush()

    except KeyboardInterrupt:
        setup_interrupted()
