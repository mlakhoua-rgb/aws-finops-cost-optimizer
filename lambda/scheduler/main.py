#!/usr/bin/env python3
"""
AWS EC2 Instance Scheduler Lambda Function

Stops and starts EC2 instances outside business hours to reduce compute spend.
Instances opt in via a tag (default: AutoScheduler=enabled). Two EventBridge
rules invoke this function with {"action": "stop"} in the evening and
{"action": "start"} in the morning; the tag marks which instances participate
and the event decides the action.

Environment variables:
    TAG_KEY        Tag key that opts an instance in  (default: AutoScheduler)
    TAG_VALUE      Tag value that opts an instance in (default: enabled)
    SNS_TOPIC_ARN  Optional. When set, a run summary is published to this topic.

Author: Mohamed Ben Lakhoua
License: MIT
"""

import json
import os
from typing import Any, Dict, List

import boto3


def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Lambda function handler."""
    action = event.get("action", "")
    tag_key = os.environ.get("TAG_KEY", "AutoScheduler")
    tag_value = os.environ.get("TAG_VALUE", "enabled")

    if action not in ("stop", "start"):
        return {
            "statusCode": 400,
            "body": json.dumps({"Error": f"Invalid action: {action!r} (expected 'stop' or 'start')"}),
        }

    ec2 = boto3.client("ec2")
    affected = apply_action(ec2, action, tag_key, tag_value)

    summary = {"Action": action, "AffectedInstances": affected, "Count": len(affected)}
    publish_summary(summary)

    return {"statusCode": 200, "body": json.dumps(summary)}


def apply_action(ec2: Any, action: str, tag_key: str, tag_value: str) -> List[str]:
    """Stop or start all opted-in instances that are in the opposite state."""
    # To stop we look for running instances; to start, stopped ones.
    current_state = "running" if action == "stop" else "stopped"
    instance_ids = get_scheduled_instances(ec2, tag_key, tag_value, current_state)

    if not instance_ids:
        print(f"No {current_state} instances tagged {tag_key}={tag_value}; nothing to {action}.")
        return []

    print(f"Applying '{action}' to instances: {instance_ids}")
    if action == "stop":
        ec2.stop_instances(InstanceIds=instance_ids)
    else:
        ec2.start_instances(InstanceIds=instance_ids)

    return instance_ids


def get_scheduled_instances(ec2: Any, tag_key: str, tag_value: str, state: str) -> List[str]:
    """Return IDs of instances with the opt-in tag in the given state."""
    instance_ids: List[str] = []
    paginator = ec2.get_paginator("describe_instances")
    pages = paginator.paginate(
        Filters=[
            {"Name": f"tag:{tag_key}", "Values": [tag_value]},
            {"Name": "instance-state-name", "Values": [state]},
        ]
    )

    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_ids.append(instance["InstanceId"])

    return instance_ids


def publish_summary(summary: Dict[str, Any]) -> None:
    """Publish a run summary to SNS when SNS_TOPIC_ARN is configured."""
    topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
    if not topic_arn or not summary.get("Count"):
        return
    try:
        boto3.client("sns").publish(
            TopicArn=topic_arn,
            Subject=f"[FinOps] EC2 scheduler: {summary['Action']} {summary['Count']} instance(s)",
            Message=json.dumps(summary, indent=2),
        )
    except Exception as exc:  # notification failure must not fail the run
        print(f"Warning: could not publish SNS summary: {exc}")
