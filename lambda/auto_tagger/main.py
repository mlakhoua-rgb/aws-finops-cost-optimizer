#!/usr/bin/env python3
"""
AWS Auto-Tagger Lambda Function

Automatically applies default tags to untagged EC2 instances and EBS volumes
so that every resource carries the minimum cost-allocation tag set. Default
tags never overwrite existing values — only missing keys are added — so the
function is safe to run repeatedly and flags gaps rather than rewriting intent.

Environment variables:
    DEFAULT_TAGS   JSON object of tag key/value pairs to apply when missing
                   (default: {"Environment": "Untagged", "Owner": "Unknown"})
    SNS_TOPIC_ARN  Optional. When set, a run summary is published to this topic.

Author: Mohamed Ben Lakhoua
License: MIT
"""

import json
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError


def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Lambda function handler."""
    default_tags: Dict[str, str] = json.loads(
        os.environ.get("DEFAULT_TAGS", '{"Environment": "Untagged", "Owner": "Unknown"}')
    )

    ec2 = boto3.client("ec2")

    tagged_resources = {
        "Instances": tag_untagged_instances(ec2, default_tags),
        "Volumes": tag_untagged_volumes(ec2, default_tags),
    }
    total = sum(len(v) for v in tagged_resources.values())
    publish_summary(tagged_resources, total)

    return {"statusCode": 200, "body": json.dumps(tagged_resources)}


def apply_missing_tags(ec2: Any, resource_id: str, existing_keys: set, default_tags: Dict[str, str]) -> bool:
    """Add any missing default tags to a resource. Returns True if tags were added."""
    tags_to_add = {k: v for k, v in default_tags.items() if k not in existing_keys}
    if not tags_to_add:
        return False

    print(f"Tagging {resource_id} with: {tags_to_add}")
    try:
        ec2.create_tags(
            Resources=[resource_id],
            Tags=[{"Key": k, "Value": v} for k, v in tags_to_add.items()],
        )
        return True
    except ClientError as exc:
        # One failed resource must not abort the whole run.
        print(f"Error tagging {resource_id}: {exc}")
        return False


def tag_untagged_instances(ec2: Any, default_tags: Dict[str, str]) -> List[str]:
    """Find EC2 instances missing default tags and tag them."""
    tagged_instance_ids: List[str] = []
    paginator = ec2.get_paginator("describe_instances")
    pages = paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]
    )

    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                existing = {t["Key"] for t in instance.get("Tags", [])}
                if apply_missing_tags(ec2, instance_id, existing, default_tags):
                    tagged_instance_ids.append(instance_id)

    return tagged_instance_ids


def tag_untagged_volumes(ec2: Any, default_tags: Dict[str, str]) -> List[str]:
    """Find EBS volumes missing default tags and tag them."""
    tagged_volume_ids: List[str] = []
    paginator = ec2.get_paginator("describe_volumes")

    for page in paginator.paginate():
        for volume in page["Volumes"]:
            volume_id = volume["VolumeId"]
            existing = {t["Key"] for t in volume.get("Tags", [])}
            if apply_missing_tags(ec2, volume_id, existing, default_tags):
                tagged_volume_ids.append(volume_id)

    return tagged_volume_ids


def publish_summary(tagged_resources: Dict[str, List[str]], total: int) -> None:
    """Publish a run summary to SNS when SNS_TOPIC_ARN is configured."""
    topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
    if not topic_arn or total == 0:
        return
    try:
        boto3.client("sns").publish(
            TopicArn=topic_arn,
            Subject=f"[FinOps] Auto-tagger applied default tags to {total} resource(s)",
            Message=json.dumps(tagged_resources, indent=2),
        )
    except Exception as exc:  # notification failure must not fail the run
        print(f"Warning: could not publish SNS summary: {exc}")
