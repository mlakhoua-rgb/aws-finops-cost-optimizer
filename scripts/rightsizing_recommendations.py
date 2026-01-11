#!/usr/bin/env python3
"""
AWS EC2 Right-Sizing Recommendations Script

This script analyzes EC2 instance utilization metrics to provide right-sizing
recommendations, helping to reduce costs by matching instance types to actual
workload requirements.

Usage:
    python rightsizing_recommendations.py --days 14 --output recommendations.json

Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
License: MIT
"""

import argparse
import boto3
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import sys


class RightSizingRecommender:
    """Recommends right-sizing for EC2 instances"""

    def __init__(self, region: str):
        """
        Initialize the Right-Sizing Recommender

        Args:
            region: AWS region to scan
        """
        self.ec2 = boto3.client("ec2", region_name=region)
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.region = region

    def get_right_sizing_recommendations(self, days: int = 14, cpu_threshold: float = 40.0, mem_threshold: float = 40.0) -> List[Dict]:
        """
        Get right-sizing recommendations for EC2 instances

        Args:
            days: Number of days to analyze (default: 14)
            cpu_threshold: CPU utilization threshold for over-provisioning (default: 40.0%)
            mem_threshold: Memory utilization threshold for over-provisioning (default: 40.0%)

        Returns:
            List of right-sizing recommendations
        """
        recommendations = []
        paginator = self.ec2.get_paginator("describe_instances")
        pages = paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])

        for page in pages:
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]

                    # Get max CPU utilization
                    cpu_metrics = self.cloudwatch.get_metric_statistics(
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        StartTime=datetime.now(timezone.utc) - timedelta(days=days),
                        EndTime=datetime.now(timezone.utc),
                        Period=3600,  # Hourly
                        Statistics=["Maximum"],
                    )

                    if not cpu_metrics["Datapoints"]:
                        continue

                    max_cpu = max(dp["Maximum"] for dp in cpu_metrics["Datapoints"])

                    # Placeholder for memory - CloudWatch Agent needed for detailed memory metrics
                    # In a real-world scenario, you would query custom memory metrics here.
                    # For this example, we'll use a simulated value or focus on CPU.
                    max_mem = 30.0  # Simulated value

                    if max_cpu < cpu_threshold and max_mem < mem_threshold:
                        recommendations.append({
                            "InstanceId": instance_id,
                            "InstanceType": instance_type,
                            "Region": self.region,
                            "Finding": "Over-provisioned EC2 Instance",
                            "MaxCPU": f"{max_cpu:.2f}%",
                            "MaxMemory": f"{max_mem:.2f}% (Simulated)",
                            "Recommendation": f"Consider smaller instance type (e.g., from {instance_type} to a smaller size in the same family)"
                        })

        return recommendations

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Get EC2 right-sizing recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--region",
        type=str,
        required=True,
        help="AWS region to scan"
    )

    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output JSON file for the recommendations"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days to analyze for utilization (default: 14)"
    )

    parser.add_argument(
        "--cpu-threshold",
        type=float,
        default=40.0,
        help="CPU utilization threshold for over-provisioning (default: 40.0)"
    )

    args = parser.parse_args()

    recommender = RightSizingRecommender(region=args.region)
    recommendations = recommender.get_right_sizing_recommendations(
        days=args.days,
        cpu_threshold=args.cpu_threshold
    )

    # Export results to JSON
    try:
        with open(args.output, "w") as f:
            json.dump(recommendations, f, indent=2)
        print(f"Recommendations saved to {args.output}")
    except Exception as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
