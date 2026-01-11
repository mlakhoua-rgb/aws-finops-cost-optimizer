#!/usr/bin/env python3
"""
AWS Unused Resources Script

This script identifies unused or underutilized AWS resources to help reduce costs.
It checks for idle EC2 instances, unattached EBS volumes, unused Elastic IPs,
and old EBS snapshots.

Usage:
    python unused_resources.py --region us-east-1 --output unused.json

Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
License: MIT
"""

import argparse
import boto3
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import sys


class UnusedResourceFinder:
    """Finds unused AWS resources"""

    def __init__(self, region: str):
        """
        Initialize the Unused Resource Finder
        
        Args:
            region: AWS region to scan
        """
        self.ec2 = boto3.client("ec2", region_name=region)
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.region = region

    def find_idle_ec2_instances(self, cpu_threshold: float = 5.0, days: int = 14) -> List[Dict]:
        """
        Find EC2 instances with low CPU utilization
        
        Args:
            cpu_threshold: CPU utilization threshold (default: 5.0%)
            days: Number of days to analyze (default: 14)
            
        Returns:
            List of idle EC2 instances
        """
        idle_instances = []
        paginator = self.ec2.get_paginator("describe_instances")
        pages = paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])

        for page in pages:
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]
                    
                    # Get CPU utilization from CloudWatch
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace="AWS/EC2",
                        MetricName="CPUUtilization",
                        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                        StartTime=datetime.now(timezone.utc) - timedelta(days=days),
                        EndTime=datetime.now(timezone.utc),
                        Period=86400,  # Daily average
                        Statistics=["Average"],
                    )
                    
                    datapoints = response.get("Datapoints", [])
                    if datapoints:
                        avg_cpu = max(dp["Average"] for dp in datapoints)
                        if avg_cpu < cpu_threshold:
                            idle_instances.append({
                                "InstanceId": instance_id,
                                "InstanceType": instance["InstanceType"],
                                "Region": self.region,
                                "Finding": "Idle EC2 Instance",
                                "Metric": f"Max CPU Utilization ({days}d)",
                                "Value": f"{avg_cpu:.2f}%",
                                "Recommendation": "Stop or terminate instance"
                            })
        return idle_instances

    def find_unattached_ebs_volumes(self) -> List[Dict]:
        """
        Find EBS volumes that are not attached to any instance
        
        Returns:
            List of unattached EBS volumes
        """
        unattached_volumes = []
        paginator = self.ec2.get_paginator("describe_volumes")
        pages = paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}])

        for page in pages:
            for volume in page["Volumes"]:
                unattached_volumes.append({
                    "VolumeId": volume["VolumeId"],
                    "Size": volume["Size"],
                    "Region": self.region,
                    "Finding": "Unattached EBS Volume",
                    "Recommendation": "Delete volume or attach to an instance"
                })
        return unattached_volumes

    def find_unused_elastic_ips(self) -> List[Dict]:
        """
        Find Elastic IPs that are not associated with any instance
        
        Returns:
            List of unused Elastic IPs
        """
        unused_eips = []
        addresses = self.ec2.describe_addresses()

        for address in addresses["Addresses"]:
            if "InstanceId" not in address and "NetworkInterfaceId" not in address:
                unused_eips.append({
                    "PublicIp": address["PublicIp"],
                    "AllocationId": address["AllocationId"],
                    "Region": self.region,
                    "Finding": "Unused Elastic IP",
                    "Recommendation": "Release Elastic IP"
                })
        return unused_eips

    def find_old_ebs_snapshots(self, retention_days: int = 30) -> List[Dict]:
        """
        Find old EBS snapshots that exceed retention period
        
        Args:
            retention_days: Number of days to retain snapshots (default: 30)
            
        Returns:
            List of old EBS snapshots
        """
        old_snapshots = []
        owner_id = boto3.client("sts").get_caller_identity().get("Account")
        paginator = self.ec2.get_paginator("describe_snapshots")
        pages = paginator.paginate(OwnerIds=[owner_id])

        for page in pages:
            for snapshot in page["Snapshots"]:
                start_time = snapshot["StartTime"]
                if start_time < datetime.now(timezone.utc) - timedelta(days=retention_days):
                    old_snapshots.append({
                        "SnapshotId": snapshot["SnapshotId"],
                        "VolumeId": snapshot.get("VolumeId", "N/A"),
                        "StartTime": start_time.isoformat(),
                        "Region": self.region,
                        "Finding": "Old EBS Snapshot",
                        "Recommendation": f"Delete snapshot (older than {retention_days} days)"
                    })
        return old_snapshots

    def scan_all(self, cpu_threshold: float = 5.0, ec2_days: int = 14, snapshot_days: int = 30) -> Dict[str, List]:
        """
        Run all scans for unused resources
        
        Args:
            cpu_threshold: CPU threshold for idle instances
            ec2_days: Number of days to analyze for idle instances
            snapshot_days: Retention period for snapshots
            
        Returns:
            Dict containing lists of all unused resources
        """
        print(f"Scanning for unused resources in {self.region}...")
        results = {
            "IdleEC2Instances": self.find_idle_ec2_instances(cpu_threshold, ec2_days),
            "UnattachedEBSVolumes": self.find_unattached_ebs_volumes(),
            "UnusedElasticIPs": self.find_unused_elastic_ips(),
            "OldEBSSnapshots": self.find_old_ebs_snapshots(snapshot_days),
        }
        print("Scan complete.")
        return results


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Find unused AWS resources to reduce costs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a specific region and save to JSON
  python unused_resources.py --region us-west-2 --output unused.json
  
  # Scan all regions
  python unused_resources.py --all-regions --output all_unused.json
        """
    )
    
    parser.add_argument(
        "--region",
        type=str,
        help="AWS region to scan (overrides --all-regions if specified)"
    )
    
    parser.add_argument(
        "--all-regions",
        action="store_true",
        help="Scan all available AWS regions"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output JSON file for the results"
    )
    
    parser.add_argument(
        "--cpu-threshold",
        type=float,
        default=5.0,
        help="CPU utilization threshold for idle instances (default: 5.0)"
    )
    
    parser.add_argument(
        "--ec2-days",
        type=int,
        default=14,
        help="Number of days to analyze for idle instances (default: 14)"
    )
    
    parser.add_argument(
        "--snapshot-days",
        type=int,
        default=30,
        help="Retention period for EBS snapshots (default: 30)"
    )
    
    args = parser.parse_args()
    
    if not args.region and not args.all_regions:
        print("Error: You must specify either --region or --all-regions", file=sys.stderr)
        sys.exit(1)
        
    regions = []
    if args.region:
        regions.append(args.region)
    elif args.all_regions:
        ec2 = boto3.client("ec2", region_name="us-east-1")
        regions = [r["RegionName"] for r in ec2.describe_regions()["Regions"]]
        
    all_results = {
        "IdleEC2Instances": [],
        "UnattachedEBSVolumes": [],
        "UnusedElasticIPs": [],
        "OldEBSSnapshots": [],
    }
    
    for region in regions:
        try:
            finder = UnusedResourceFinder(region=region)
            results = finder.scan_all(
                cpu_threshold=args.cpu_threshold,
                ec2_days=args.ec2_days,
                snapshot_days=args.snapshot_days
            )
            
            for key, value in results.items():
                all_results[key].extend(value)
        except Exception as e:
            print(f"Error scanning region {region}: {e}", file=sys.stderr)
            
    # Export results to JSON
    try:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"Results saved to {args.output}")
    except Exception as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
