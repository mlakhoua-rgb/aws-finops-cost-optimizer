#!/usr/bin/env python3
"""
AWS EBS Snapshot Cleanup Lambda Function

Identifies and deletes EBS snapshots owned by this account that are older than
the retention period, reducing storage costs. Snapshots tagged Retain (any
value) are always skipped. Runs in dry-run mode by default — it must be
explicitly switched to destructive mode by setting DRY_RUN=false.

Environment variables:
    RETENTION_DAYS  Snapshots older than this many days are eligible (default: 30)
    DRY_RUN         "true" (default) reports what would be deleted; "false" deletes
    SNS_TOPIC_ARN   Optional. When set, a run summary is published to this topic.

Author: Mohamed Ben Lakhoua
License: MIT
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError


def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Lambda function handler."""
    retention_days = int(os.environ.get("RETENTION_DAYS", "30"))
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"

    ec2 = boto3.client("ec2")
    account_id = boto3.client("sts").get_caller_identity()["Account"]

    deleted_snapshots = cleanup_snapshots(ec2, account_id, retention_days, dry_run)

    summary = {
        "DeletedSnapshots": deleted_snapshots,
        "Count": len(deleted_snapshots),
        "RetentionDays": retention_days,
        "DryRun": dry_run,
    }
    publish_summary(summary)

    return {"statusCode": 200, "body": json.dumps(summary)}


def cleanup_snapshots(ec2: Any, account_id: str, retention_days: int, dry_run: bool) -> List[str]:
    """Find and delete old EBS snapshots owned by this account."""
    deleted_snapshot_ids: List[str] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    paginator = ec2.get_paginator("describe_snapshots")

    for page in paginator.paginate(OwnerIds=[account_id]):
        for snapshot in page["Snapshots"]:
            snapshot_id = snapshot["SnapshotId"]

            # Retention override: never touch snapshots tagged Retain.
            if any(tag.get("Key") == "Retain" for tag in snapshot.get("Tags", [])):
                print(f"Skipping snapshot {snapshot_id} due to 'Retain' tag.")
                continue

            if snapshot["StartTime"] >= cutoff:
                continue

            if dry_run:
                print(f"(Dry run) Would delete snapshot {snapshot_id} (created {snapshot['StartTime']})")
                deleted_snapshot_ids.append(snapshot_id)
                continue

            try:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted snapshot {snapshot_id} (created {snapshot['StartTime']})")
                deleted_snapshot_ids.append(snapshot_id)
            except ClientError as exc:
                # Snapshots backing registered AMIs raise InvalidSnapshot.InUse — skip them.
                print(f"Error deleting snapshot {snapshot_id}: {exc}")

    return deleted_snapshot_ids


def publish_summary(summary: Dict[str, Any]) -> None:
    """Publish a run summary to SNS when SNS_TOPIC_ARN is configured."""
    topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
    if not topic_arn or not summary.get("Count"):
        return
    mode = "dry run" if summary["DryRun"] else "deleted"
    try:
        boto3.client("sns").publish(
            TopicArn=topic_arn,
            Subject=f"[FinOps] Snapshot cleanup: {summary['Count']} snapshot(s) ({mode})",
            Message=json.dumps(summary, indent=2),
        )
    except Exception as exc:  # notification failure must not fail the run
        print(f"Warning: could not publish SNS summary: {exc}")
