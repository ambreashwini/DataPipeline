# help set up local environment through aws cli

import os
import logging
import subprocess
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def check_aws_cli():
    """
    - check if AWS CLI is installed
    - install if missing
    """
    try:
        subprocess.run(["aws", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info("AWS CLI installed")
        return True
    except FileNotFoundError:
        logging.error("AWS CLI is not installed, installing now")
        install_aws_cli()
        return False


def install_aws_cli():
    """
    - install AWS CLI
    """
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        logging.info("Installing AWS CLI for Linux/macOS...")
        subprocess.run("curl 'https://awscli.amazonaws.com/AWSCLIV2.pkg' -o 'AWSCLIV2.pkg'", shell=True)
        subprocess.run("sudo installer -pkg AWSCLIV2.pkg -target /", shell=True)
    else:
        logging.info("Please install AWS CLI manually from https://aws.amazon.com/cli/")
        sys.exit(1)


def check_aws_credentials():
    """
    - check if profile exists
    """
    aws_credentials_path = os.path.expanduser("~/.aws/credentials")
    if os.path.exists(aws_credentials_path):
        logging.info("AWS profile is already configured.")
        show_profile()
        # TODO -
        # switch profile if needed
    else:
        logging.info("AWS credentials not found.")
        configure_aws_credentials()


def configure_aws_credentials():
    """
    - get user input for AWS CLI credentials
    """
    logging.info("enter details as prompted")

    aws_access_key = input("you AWS Access Key ID - ").strip()
    aws_secret_key = input("your AWS Secret Access Key - ").strip()
    aws_region = input("your AWS region [default: us-east-1] - ").strip() or "us-east-1"
    aws_profile = input("your AWS profile name [default: default] - ").strip() or "default"

    # configure profile
    subprocess.run(["aws", "configure", "set", "aws_access_key_id", aws_access_key, "--profile", aws_profile])
    subprocess.run(["aws", "configure", "set", "aws_secret_access_key", aws_secret_key, "--profile", aws_profile])
    subprocess.run(["aws", "configure", "set", "region", aws_region, "--profile", aws_profile])

    logging.info(f"AWS profile configured successfully '{aws_profile}'.")

def show_profile():
    """
    display current AWS profile details
    """
    logging.info("Available AWS profile details")
    try:
        subprocess.run(["aws", "configure", "list"])
    except subprocess.CalledProcessError:
        logging.error("Error fetching AWS profile, please verify your credentials")


if __name__ == "__main__":
    logging.info("Setting up project")
    # check if AWS CLI is installed
    if check_aws_cli():
        # check or configure AWS credentials
        check_aws_credentials()