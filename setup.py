import os
import sys
import subprocess
import boto3
import yaml
from configparser import ConfigParser
from dotenv import load_dotenv


def check_virtual_env():
    if sys.prefix == sys.base_prefix:
        print("Error: Virtual environment is not activated.")
        exit(1)
    print("Virtual environment is active.")


def install_requirements(requirements_path):
    if not os.path.exists(requirements_path):
        print(f"Error: Requirements file {requirements_path} not found.")
        exit(1)
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True)


def get_env():
    load_dotenv()
    ENVIRONMENT = os.getenv("ENVIRONMENT")
    if not ENVIRONMENT:
        print("Error: ENVIRONMENT is not set. Check the .env file.")
        exit(1)
    print(f"ENVIRONMENT = {ENVIRONMENT}")


def load_setup_config(file_path):
    if not os.path.exists(file_path):
        print(f"Could not find {file_path}.")
        exit(1)

    with open(file_path, "r") as file:
        return yaml.safe_load(file) if file_path.endswith((".yml", ".yaml")) else exit("Error: Use a YAML config file.")


def check_aws_credentials(credentials_path):
    if not os.path.exists(credentials_path):
        print(f"AWS credentials file {credentials_path} not found.")
        exit(1)

    with open(credentials_path, "r") as file:
        credentials = yaml.safe_load(file)

    aws_access_key = credentials.get("aws_access_key_id")
    aws_secret_key = credentials.get("aws_secret_access_key")

    if not aws_access_key or not aws_secret_key:
        print("Error: AWS credentials missing in config file.")
        exit(1)

    print("AWS credentials found.")
    return aws_access_key, aws_secret_key


def list_aws_profiles():
    session = boto3.Session()
    return session.available_profiles


def aws_profile_exists(profile_name):
    return profile_name in list_aws_profiles()


def write_aws_profile(profile_name, aws_access_key, aws_secret_key, aws_region):
    credentials_file = os.path.expanduser("~/.aws/credentials")
    config = ConfigParser()
    if os.path.exists(credentials_file):
        config.read(credentials_file)

    if not config.has_section(profile_name):
        config.add_section(profile_name)

    config.set(profile_name, "aws_access_key_id", aws_access_key)
    config.set(profile_name, "aws_secret_access_key", aws_secret_key)

    with open(credentials_file, "w") as file:
        config.write(file)

    print(f"AWS profile '{profile_name}' written to {credentials_file}.")

    # Ensure region is set
    subprocess.run(["aws", "configure", "set", "region", aws_region, "--profile", profile_name], check=True)
    print(f"AWS profile '{profile_name}' region set to {aws_region}.")


def configure_aws_profile(profile_name, aws_access_key, aws_secret_key, aws_region):
    if aws_profile_exists(profile_name):
        print(f"AWS profile '{profile_name}' already exists. Ensuring region is set.")

        # Check if the profile has a region set
        result = subprocess.run(
            ["aws", "configure", "get", "region", "--profile", profile_name],
            capture_output=True,
            text=True
        )
        current_region = result.stdout.strip()

        if not current_region:
            print(f"Profile '{profile_name}' is missing a region. Setting to {aws_region}.")
            subprocess.run(["aws", "configure", "set", "region", aws_region, "--profile", profile_name], check=True)

        return boto3.Session(profile_name=profile_name)

    print(f"AWS profile '{profile_name}' does not exist. Creating new profile.")
    write_aws_profile(profile_name, aws_access_key, aws_secret_key, aws_region)
    return boto3.Session(profile_name=profile_name)


def get_aws_details(session):
    sts_client = session.client("sts")
    identity = sts_client.get_caller_identity()
    account_id = identity["Account"]
    arn = identity["Arn"]
    role = arn.split("/")[-1]

    # Ensure the correct region is used
    result = subprocess.run(
        ["aws", "configure", "get", "region", "--profile", session.profile_name],
        capture_output=True,
        text=True
    )
    region = result.stdout.strip() or "us-east-1"

    print(f"Account ID: {account_id}, Region: {region}, ARN: {arn}, Role: {role}")
    return {"account_id": account_id, "profile_name": session.profile_name, "region": region, "arn": arn, "role": role}


def create_terraform_config(terraform_config_path, aws_details, project_files, aws_resources):
    # Prepare new config data, overwriting the old file
    terraform_config = {
        "aws_profile": aws_details,
        "project_files": project_files,  # Overwrite with the new project files data
        "aws_resources": aws_resources   # Overwrite with the new AWS resources data
    }

    # Write the new config to the terraform setup file
    with open(terraform_config_path, "w") as file:
        yaml.safe_dump(terraform_config, file)

    print("AWS Terraform config updated (overwritten) successfully.")


if __name__ == "__main__":
    print("Setting up project")
    check_virtual_env()

    setup_config_path = "setup.yml"
    terraform_config_path = "terraform_setup.yml"

    # Load the setup configuration
    setup_config = load_setup_config(setup_config_path)

    # Verify the loaded config
    print("Loaded setup config:", setup_config)

    requirements_path = setup_config.get("project_files", {}).get("requirements_path")

    if requirements_path:
        install_requirements(requirements_path)

    get_env()

    # Get the AWS credentials and profile details
    aws_credentials_path = setup_config.get("aws_credentials")
    aws_profile_name = setup_config.get("aws_profile_name")
    aws_region = setup_config.get("aws_region") or "us-east-1"  # default to us-est-1

    # Ensure project files and AWS resources are read correctly
    project_files = setup_config.get("project_files", {})
    aws_resources = setup_config.get("aws_resources", {})

    # Print the loaded project files and aws resources to verify
    print("Loaded project_files:", project_files)
    print("Loaded aws_resources:", aws_resources)

    # Check AWS credentials
    aws_access_key, aws_secret_key = check_aws_credentials(aws_credentials_path)

    # Configure AWS profile
    session = configure_aws_profile(aws_profile_name, aws_access_key, aws_secret_key, aws_region)

    # Get AWS details (account, role, region)
    aws_details = get_aws_details(session)

    # Create the Terraform config (overwrite existing file)
    create_terraform_config(terraform_config_path, aws_details, project_files, aws_resources)

    print("Local AWS Configuration setup complete. Complete Terraform setup.")

