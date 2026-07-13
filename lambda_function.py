import boto3
from datetime import datetime, timezone

# AWS Clients
ec2 = boto3.client("ec2")
sns = boto3.client("sns")

# Replace with your SNS Topic ARN
SNS_TOPIC_ARN = "YOUR_SNS_TOPIC_ARN"

# Snapshot age threshold (days)
SNAPSHOT_AGE_DAYS = 30


def find_old_snapshots():
    snapshots = []

    response = ec2.describe_snapshots(OwnerIds=["self"])
    current_time = datetime.now(timezone.utc)

    for snapshot in response["Snapshots"]:
        age = (current_time - snapshot["StartTime"]).days

        if age >= SNAPSHOT_AGE_DAYS:
            snapshots.append({
                "SnapshotId": snapshot["SnapshotId"],
                "Age": age
            })

    return snapshots


def find_unused_elastic_ips():
    elastic_ips = []

    response = ec2.describe_addresses()

    for address in response["Addresses"]:
        if "AssociationId" not in address:
            elastic_ips.append({
                "AllocationId": address["AllocationId"],
                "PublicIp": address["PublicIp"]
            })

    return elastic_ips


def generate_report(snapshots, elastic_ips):

    report = "AWS Cost Optimization Report\n"
    report += "=" * 50 + "\n\n"

    report += "Stale EBS Snapshots (30+ Days)\n"
    report += "-" * 35 + "\n"

    if snapshots:
        for snapshot in snapshots:
            report += f"{snapshot['SnapshotId']} ({snapshot['Age']} Days)\n"
    else:
        report += "No stale snapshots found.\n"

    report += "\nUnused Elastic IPs\n"
    report += "-" * 20 + "\n"

    if elastic_ips:
        for ip in elastic_ips:
            report += f"{ip['PublicIp']}\n"
    else:
        report += "No unused Elastic IPs found.\n"

    return report


def send_notification(report):
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="AWS Cost Optimization Report",
        Message=report
    )


def delete_snapshots(snapshots):

    for snapshot in snapshots:
        try:
            ec2.delete_snapshot(
                SnapshotId=snapshot["SnapshotId"]
            )

            print(f"Deleted Snapshot: {snapshot['SnapshotId']}")

        except Exception as e:
            print(f"Failed to delete {snapshot['SnapshotId']}: {e}")


def release_elastic_ips(elastic_ips):

    for ip in elastic_ips:
        try:
            ec2.release_address(
                AllocationId=ip["AllocationId"]
            )

            print(f"Released Elastic IP: {ip['PublicIp']}")

        except Exception as e:
            print(f"Failed to release {ip['PublicIp']}: {e}")


def lambda_handler(event, context):

    print("Starting AWS Cost Optimization...")

    # Step 1 - Scan Resources
    snapshots = find_old_snapshots()
    elastic_ips = find_unused_elastic_ips()

    # Step 2 - Generate Report
    report = generate_report(snapshots, elastic_ips)

    print(report)

    # Step 3 - Send Email
    send_notification(report)

    print("SNS Notification Sent")

    # Step 4 - Delete Old Snapshots
    delete_snapshots(snapshots)

    # Step 5 - Release Elastic IPs
    release_elastic_ips(elastic_ips)

    print("Cleanup Completed")

    return {
        "statusCode": 200,
        "body": "AWS Cost Optimization Completed Successfully"
    }
