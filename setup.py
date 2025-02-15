import os
import logging
import subprocess
import json
import sys
import boto3
import botocore.exceptions

# Reset logging
logging.getLogger().handlers.clear()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)


def setup_interrupted():
    # if set up interrupted, handle properly
    logging.info("\nProcess interrupted, setup incomplete. Please rerun.")
    sys.stdout.flush()
    sys.exit(1)


def check_virtual_env():
    # check if virtual env is activated
    if sys.prefix == sys.base_prefix:
        logging.error("Virtual environment is not active. Please activate venv before running this script.")
        sys.exit(1)
    logging.info("Virtual environment is active.")


def install_requirements():
    # install project requirements
    if os.path.exists("requirements.txt"):
        logging.info("Installing required dependencies from requirements.txt...")
        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
        logging.info("Dependencies installed successfully.")
    else:
        logging.warning("requirements.txt not found. Ensure dependencies are installed manually.")


def check_aws_cli():
    # check if aws cli installed, if not install
    if subprocess.run(["aws", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        logging.info("AWS CLI installed.")
    else:
        logging.warning("AWS CLI is not installed. Installing now...")
        if subprocess.run(["pip", "install", "awscli"]).returncode != 0:
            logging.error("Failed to install AWS CLI. Please install it manually.")
            sys.exit(1)


def check_terraform():
    # terraform check
    if subprocess.run(["terraform", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        logging.info("Terraform is installed.")
    else:
        logging.warning("Terraform is not installed. Installing now...")
        if sys.platform == "darwin":  # macOS
            subprocess.run(["brew", "install", "terraform"], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["choco", "install", "terraform"], check=True)
        else:
            logging.error(
                "Terraform is missing. Please install it manually from https://developer.hashicorp.com/terraform/downloads.")
            sys.exit(1)


def check_iam_permissions(profile):
    # check IAM permissions
    logging.info("Checking IAM permissions for role creation...")
    session = boto3.Session(profile_name=profile)
    iam_client = session.client('iam')

    try:
        identity = session.client("sts").get_caller_identity()
        PolicySourceArn = identity["Arn"]
        iam_client.simulate_principal_policy(
            PolicySourceArn=PolicySourceArn,
            ActionNames=["iam:CreateRole", "iam:AttachRolePolicy", "iam:PutRolePolicy"]
        )
        logging.info("IAM user has the required permissions to create roles.")

    except botocore.exceptions.ClientError as e:
        logging.error(f"IAM permissions check failed: {e.response['Error']['Message']}")
        logging.error("Your AWS user lacks necessary permissions. Grant 'iam:CreateRole' and retry.")
        sys.exit(1)


def validate_profile(profile):
    # ensure user input is valid before finalizing profile
    try:
        session = boto3.Session(profile_name=profile)
        sts_client = session.client('sts')
        sts_client.get_caller_identity()
        logging.info(f"Successfully authenticated with profile '{profile}'.")
        return True
    except botocore.exceptions.NoCredentialsError:
        logging.error(f"No credentials found for profile '{profile}'. Check AWS configuration.")
    except botocore.exceptions.PartialCredentialsError:
        logging.error(f"Incomplete credentials for profile '{profile}'. Ensure both Access Key and Secret Key are set.")
    except botocore.exceptions.ClientError as e:
        logging.error(f"AWS Client error: {e.response['Error']['Message']}")
    except Exception as e:
        logging.error(f"Unexpected error during credential validation: {str(e)}")
    return False

def get_iam_role(profile):
    # get IAM role
    session = boto3.Session(profile_name=profile)
    sts_client = session.client('sts')
    try:
        identity = sts_client.get_caller_identity()
        return identity["Arn"].split("/")[-1]  # Extracts role or user name
    except Exception as e:
        logging.error(f"Error retrieving IAM role: {str(e)}")
        return "Unknown"

def list_aws_profiles():
    # check current profiles prevent overwriting existing ones
    session = boto3.Session()
    return session.available_profiles


def get_aws_region(profile):
    # set region
    session = boto3.Session(profile_name=profile)
    return session.region_name or "us-east-1"


def setup_new_profile(existing_profiles):
    # set up new profile locally
    while True:
        if existing_profiles:
            logging.info(f"Existing profiles: {', '.join(existing_profiles)}")
            logging.info("Please enter a profile name that is NOT in the above list.")
        else:
            logging.info("No existing profiles detected. Please enter a name for your AWS profile.")

        sys.stdout.flush()
        profile = input("Enter AWS profile name: ").strip()
        if profile in existing_profiles:
            logging.warning(f"Profile '{profile}' already exists. Choose a different name.")
            continue

        logging.info("Profile name accepted. Enter AWS credentials -")
        aws_access_key = input("AWS Access Key ID: ").strip()
        aws_secret_key = input("AWS Secret Access Key: ").strip()
        aws_region = input("AWS region, press enter to select [default: us-east-1]: ").strip()
        if not aws_region:
            aws_region = "us-east-1"
            logging.info("AWS Region selected as 'us-east-1'")

        # Store credentials in AWS CLI config
        subprocess.run(["aws", "configure", "set", "aws_access_key_id", aws_access_key, "--profile", profile])
        subprocess.run(["aws", "configure", "set", "aws_secret_access_key", aws_secret_key, "--profile", profile])
        subprocess.run(["aws", "configure", "set", "region", aws_region, "--profile", profile])

        if not validate_profile(profile):
            logging.error("Invalid AWS credentials provided. Please re-enter valid credentials.")
            continue
        logging.info(f"AWS profile '{profile}' configured successfully. Using this profile.")
        iam_role = get_iam_role(profile)
        return profile, iam_role, aws_region


def generate_terraform_files(profile, IAM_role, region):
    # generate terraform file using template
    logging.info("Generating Terraform files...")
    terraform_dir = "aws_config/dev"
    os.makedirs(terraform_dir, exist_ok=True)
    template_file = "aws_config/templates/template.tf"
    dev_tf_file = os.path.join(terraform_dir, "dev.tf")

    if not os.path.exists(template_file):
        logging.error(f"Template file '{template_file}' not found. Ensure it exists before running setup.")
        sys.exit(1)

    with open(template_file, "r") as tf_template:
        template_content = tf_template.read()

    updated_content = (
        template_content.replace("{AWS_REGION}", region)
        .replace("{AWS_PROFILE}", profile)
        .replace("{ROLE_NAME}", IAM_role)
    )

    with open(dev_tf_file, "w") as tf_file:
        tf_file.write(updated_content)

    logging.info(f"Terraform file '{dev_tf_file}' generated successfully.")
    apply_terraform(terraform_dir)


def apply_terraform(terraform_dir):
    # basic terraform test
    logging.info("Initializing and applying Terraform")
    check_terraform()
    subprocess.run(["terraform", "init"], cwd=terraform_dir, check=True)
    subprocess.run(["terraform", "apply", "-auto-approve"], cwd=terraform_dir, check=True)
    logging.info("Terraform applied successfully.")


if __name__ == "__main__":
    try:
        logging.info("Checking virtual environment and installing dependencies")
        sys.stdout.flush()
        check_virtual_env()
        install_requirements()
        check_aws_cli()
        check_terraform()
        profiles = list_aws_profiles()
        profile, IAM_role, region = setup_new_profile(profiles)
        check_iam_permissions(profile)
        generate_terraform_files(profile, IAM_role, region)
        sys.stdout.flush()
    except KeyboardInterrupt:
        setup_interrupted()
