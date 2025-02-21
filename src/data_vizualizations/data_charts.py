"""Charts for dynamoDB data."""
import random
import time
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from collections import defaultdict
from boto3.dynamodb.conditions import Key


TABLE_NAME = "project-data-pipeline-table"
AWS_PROFILE = "data-pipeline-local-profile"
REGION = "us-east-1"

try:
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=REGION)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)
    scan_response = table.scan()
except (NoCredentialsError, PartialCredentialsError) as e:
    print(f"Error: AWS credentials not found or incomplete. {e}")
    exit(1)
except Exception as e:
    print(f"Unexpected error deleting old data: {e}")
    exit(1)


def get_top_sites():
    """Get top 10 sites."""
    try:
        response = table.scan(ProjectionExpression="site_id")
        site_counts = defaultdict(int)
        for item in response.get("Items", []):
            site_counts[item["site_id"]] += 1
        print("Returning top 10 sites")
        return sorted(site_counts.keys(), key=lambda x: site_counts[x], reverse=True)[
            :10
        ]
    except ClientError as e:
        print(f"Error scanning DynamoDB: {e}")
        return []


def query_recent_site_data(site_id):
    """Get last 24 hours data."""
    time_cutoff = int(time.time()) - 86400
    try:
        response = table.query(
            KeyConditionExpression=Key("site_id").eq(site_id)
            & Key("timestamp").gt(time_cutoff),
            ScanIndexForward=True,
        )
        return response.get("Items", [])
    except ClientError as e:
        print(f"Error querying DynamoDB: {e}")
        return []


top_ten_sites = get_top_sites()
print(top_ten_sites)
site_data = query_recent_site_data(top_ten_sites[1])
