"""Charts for dynamoDB data."""
import random
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import boto3
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import numpy as np
import pytz
from boto3.dynamodb.conditions import Key
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

PST = pytz.timezone("US/Pacific")
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
    """Get top 5 sites."""
    try:
        response = table.scan(ProjectionExpression="site_id")
        site_counts = defaultdict(int)
        for item in response.get("Items", []):
            site_counts[item["site_id"]] += 1
        print("Returning top 5 sites")
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


def plot_generated_vs_consumed(sites):
    """Plot generated vs consumed energy for the top 10 sites (last 24 hours)."""
    site_energy = {site: {"generated": 0, "consumed": 0} for site in sites}
    timestamps_pst = []  # Store all timestamps to determine min/max

    for site in sites:
        site_data = query_recent_site_data(site)
        for item in site_data:
            timestamp_utc = int(item["timestamp"])
            timestamp_utc = datetime.fromtimestamp(timestamp_utc, timezone.utc)
            timestamp_pst = timestamp_utc.astimezone(PST)
            timestamps_pst.append(timestamp_pst)

            if not item.get("anomaly"):
                site_energy[site]["generated"] += float(item["energy_generated_kwh"])
                site_energy[site]["consumed"] += float(item["energy_consumed_kwh"])

    # Extract data
    x_labels = list(site_energy.keys())
    energy_generated = [site_energy[s]["generated"] for s in x_labels]
    energy_consumed = [site_energy[s]["consumed"] for s in x_labels]

    # Bar chart
    x = np.arange(len(x_labels))
    width = 0.35

    plt.figure(figsize=(12, 6))
    plt.bar(x - width / 2, energy_generated, width, label="Generated", color="green")
    plt.bar(x + width / 2, energy_consumed, width, label="Consumed", color="orange")

    plt.xlabel("Site ID")
    plt.ylabel("Energy (kWh)")
    plt.title(f"Energy Generation vs Consumption per Site (last 24 hours)")
    plt.xticks(x, x_labels, rotation=90, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_anomalies_per_site(sites):
    """Chart for anomalies over last 24 hours."""
    anomaly_counts = defaultdict(int)
    for site in sites:
        site_data = query_recent_site_data(site)
        for item in site_data:
            if item.get("anomaly"):
                anomaly_counts[site] += 1
    if not anomaly_counts:
        print("No anomalies found in the last 24 hours.")
        return
    x_labels = sorted(anomaly_counts.keys())
    y_values = [anomaly_counts[s] for s in x_labels]
    plt.figure(figsize=(8, 5))
    plt.plot(x_labels, y_values, marker="o", color="crimson", linewidth=2)
    plt.xlabel("Site ID")
    plt.ylabel("Anomaly Count")
    plt.title(f"Anomaly Distribution Over Sites (Last 24 Hours)")
    plt.xticks(rotation=90, ha="right")
    plt.tight_layout()
    plt.show()


def plot_energy_trends(site_id, site_data):
    """Energy trends for a site over the last 3 hours, excluding anomalies."""
    now_utc, cutoff_time = datetime.now(timezone.utc), datetime.now(
        timezone.utc
    ) - timedelta(hours=3)

    valid_data = [
        (
            int(item["timestamp"]),
            float(item["energy_generated_kwh"]),
            float(item["energy_consumed_kwh"]),
        )
        for item in site_data
        if item.get("site_id") == site_id
        and not item.get("anomaly")
        and item["energy_generated_kwh"] >= 0
        and item["energy_consumed_kwh"] >= 0
        and datetime.fromtimestamp(int(item["timestamp"]), timezone.utc) >= cutoff_time
    ]

    if not valid_data:
        return print(f"No valid data for site '{site_id}' in the last 3 hours.")

    timestamps, energy_generated, energy_consumed = zip(*sorted(valid_data))
    readable_times = [
        datetime.fromtimestamp(ts, timezone.utc).strftime("%H:%M") for ts in timestamps
    ]

    plt.figure(figsize=(12, 6))
    plt.plot(
        readable_times,
        energy_generated,
        label="Generated (kWh)",
        color="blue",
        linewidth=2,
    )
    plt.plot(
        readable_times,
        energy_consumed,
        label="Consumed (kWh)",
        color="green",
        linestyle="dashed",
        linewidth=2,
    )

    plt.xlabel("Time (UTC)"), plt.ylabel("Energy (kWh)")
    plt.title(f"Energy Trends for {site_id} (Last 3 Hours, No Anomalies)")
    plt.legend(), plt.xticks(rotation=45, ha="right"), plt.grid(
        True, linestyle="--", alpha=0.5
    )
    plt.tight_layout(), plt.show()


top_ten_sites = get_top_sites()
print(top_ten_sites)
site_data = query_recent_site_data(top_ten_sites[1])
# generated vs consumed
plot_generated_vs_consumed(top_ten_sites)
# anomalies
plot_anomalies_per_site(top_ten_sites)
# energy trend
site_id = top_ten_sites[1]
site_data = query_recent_site_data(site_id)
plot_energy_trends(site_id, site_data)
