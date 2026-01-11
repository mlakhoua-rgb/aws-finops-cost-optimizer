#!/usr/bin/env python3
"""
AWS EBS Snapshot Cleanup Lambda Function

This Lambda function identifies and deletes old EBS snapshots that exceed
the defined retention period, reducing storage costs.

Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
License: MIT
"""

import boto3
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any

def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Lambda function handler"""
    region = os.environ.get("AWS_REGION", "us-east-1")
    retention_days = int(os.environ.get("RETENTION_DAYS", 30))
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    
    ec2 = boto3.client("ec2", region_name=region)
    
    deleted_snapshots = cleanup_snapshots(ec2, retention_days, dry_run)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "DeletedSnapshots": deleted_snapshots,
            "DryRun": dry_run
        })
    }

def cleanup_snapshots(ec2: boto3.client, retention_days: int, dry_run: bool) -> List[str]:
    """Find and delete old EBS snapshots"""
    deleted_snapshot_ids = []
    owner_id = boto3.client("sts").get_caller_identity().get("Account")
    paginator = ec2.get_paginator("describe_snapshots")
    pages = paginator.paginate(OwnerIds=[owner_id])

    for page in pages:
        for snapshot in page["Snapshots"]:
            snapshot_id = snapshot["SnapshotId"]
            start_time = snapshot["StartTime"]
            
            # Check for retention override tag
            if any(tag.get("Key") == "Retain" for tag in snapshot.get("Tags", [])):
                print(f"Skipping snapshot {snapshot_id} due to 'Retain' tag.")
                continue

            if start_time < datetime.now(timezone.utc) - timedelta(days=retention_days):
                print(f"Found old snapshot: {snapshot_id} (created {start_time})")
                if not dry_run:
                    try:
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        print(f"Deleted snapshot: {snapshot_id}")
                        deleted_snapshot_ids.append(snapshot_id)
                    except Exception as e:
                        print(f"Error deleting snapshot {snapshot_id}: {e}")
                else:
                    print(f"(Dry Run) Would have deleted snapshot: {snapshot_id}")
                    deleted_snapshot_ids.append(snapshot_id)
                    
    return deleted_snapshot_ids
