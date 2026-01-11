#!/usr/bin/env python3
"""
AWS Auto-Tagger Lambda Function

This Lambda function automatically tags untagged EC2 instances and EBS volumes
to enforce tagging policies and improve cost allocation.

Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
License: MIT
"""

import boto3
import os
import json
from typing import Dict, List, Any


def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """Lambda function handler"""
    region = os.environ.get("AWS_REGION", "us-east-1")
    default_tags = json.loads(os.environ.get("DEFAULT_TAGS", 
        json.dumps({"Environment": "Untagged", "Owner": "Unknown"})))
    
    ec2 = boto3.client("ec2", region_name=region)
    
    tagged_resources = {
        "Instances": tag_untagged_instances(ec2, default_tags),
        "Volumes": tag_untagged_volumes(ec2, default_tags)
    }
    
    return {
        "statusCode": 200,
        "body": json.dumps(tagged_resources)
    }

def tag_untagged_instances(ec2: boto3.client, default_tags: Dict[str, str]) -> List[str]:
    """Find and tag untagged EC2 instances"""
    tagged_instance_ids = []
    paginator = ec2.get_paginator("describe_instances")
    pages = paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}])

    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                existing_tags = {t["Key"] for t in instance.get("Tags", [])}
                
                tags_to_add = {k: v for k, v in default_tags.items() if k not in existing_tags}
                
                if tags_to_add:
                    print(f"Tagging instance {instance_id} with: {tags_to_add}")
                    ec2.create_tags(
                        Resources=[instance_id],
                        Tags=[{"Key": k, "Value": v} for k, v in tags_to_add.items()]
                    )
                    tagged_instance_ids.append(instance_id)
                    
    return tagged_instance_ids

def tag_untagged_volumes(ec2: boto3.client, default_tags: Dict[str, str]) -> List[str]:
    """Find and tag untagged EBS volumes"""
    tagged_volume_ids = []
    paginator = ec2.get_paginator("describe_volumes")
    pages = paginator.paginate()

    for page in pages:
        for volume in page["Volumes"]:
            volume_id = volume["VolumeId"]
            existing_tags = {t["Key"] for t in volume.get("Tags", [])}
            
            tags_to_add = {k: v for k, v in default_tags.items() if k not in existing_tags}
            
            if tags_to_add:
                print(f"Tagging volume {volume_id} with: {tags_to_add}")
                ec2.create_tags(
                    Resources=[volume_id],
                    Tags=[{"Key": k, "Value": v} for k, v in tags_to_add.items()]
                )
                tagged_volume_ids.append(volume_id)
                
    return tagged_volume_ids
