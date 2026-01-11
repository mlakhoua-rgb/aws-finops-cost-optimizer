#!/usr/bin/env python3
"""
AWS EC2 Instance Scheduler Lambda Function

This Lambda function stops and starts EC2 instances based on tags to reduce costs.
It can be triggered by CloudWatch Events on a schedule.

Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
License: MIT
"""

import boto3
import os
from typing import Dict, List, Any


def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Lambda function handler"""
    region = os.environ.get("AWS_REGION", "us-east-1")
    action = event.get("action", "stop")  # Can be "stop" or "start"
    tag_key = os.environ.get("TAG_KEY", "AutoScheduler")
    
    ec2 = boto3.client("ec2", region_name=region)
    
    if action == "stop":
        stopped_instances = stop_instances(ec2, tag_key)
        return {"statusCode": 200, "body": json.dumps({"StoppedInstances": stopped_instances})}
    elif action == "start":
        started_instances = start_instances(ec2, tag_key)
        return {"statusCode": 200, "body": json.dumps({"StartedInstances": started_instances})}
    else:
        return {"statusCode": 400, "body": "Invalid action specified"}

def stop_instances(ec2: boto3.client, tag_key: str) -> List[str]:
    """Find and stop instances with the specified tag"""
    instances_to_stop = get_instances_by_tag(ec2, tag_key, "stop")
    
    if instances_to_stop:
        print(f"Stopping instances: {instances_to_stop}")
        ec2.stop_instances(InstanceIds=instances_to_stop)
        
    return instances_to_stop

def start_instances(ec2: boto3.client, tag_key: str) -> List[str]:
    """Find and start instances with the specified tag"""
    instances_to_start = get_instances_by_tag(ec2, tag_key, "start")
    
    if instances_to_start:
        print(f"Starting instances: {instances_to_start}")
        ec2.start_instances(InstanceIds=instances_to_start)
        
    return instances_to_start

def get_instances_by_tag(ec2: boto3.client, tag_key: str, tag_value: str) -> List[str]:
    """Get instance IDs with a specific tag value"""
    instance_ids = []
    paginator = ec2.get_paginator("describe_instances")
    pages = paginator.paginate(Filters=[
        {"Name": f"tag:{tag_key}", "Values": [tag_value]},
        {"Name": "instance-state-name", "Values": ["running"] if tag_value == "stop" else ["stopped"]}
    ])

    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_ids.append(instance["InstanceId"])
                
    return instance_ids
