#!/usr/bin/env python3
"""
AWS Unused Resources Script

Identifies unused or underutilized AWS resources and estimates the monthly
waste in dollars. Checks for idle EC2 instances, unattached EBS volumes,
unused Elastic IPs, old EBS snapshots, and idle RDS instances.

Savings estimates use us-east-1 on-demand list prices (see PRICING below) and
are deliberately conservative approximations for prioritisation — actual
prices vary by region and purchase option. Validate every finding with the
resource owner before acting on it.

Usage:
    python unused_resources.py --region us-east-1 --output unused.json
    python unused_resources.py --all-regions --output unused.json

Author: Mohamed Ben Lakhoua
License: MIT
"""

import argparse
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import sys


# ---------------------------------------------------------------------------
# Pricing assumptions (us-east-1, on-demand list prices, USD/month)
# Sources: aws.amazon.com/ebs/pricing, aws.amazon.com/vpc/pricing
# Approximations for prioritisation only — actual prices vary by region.
# ---------------------------------------------------------------------------

PRICING: Dict[str, Any] = {
    "ebs_gb_month": {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.015,
        "standard": 0.05,
    },
    "snapshot_gb_month": 0.05,
    "elastic_ip_month": 3.65,  # $0.005/hour public IPv4 charge
}


class UnusedResourceFinder:
    """Finds unused AWS resources and estimates monthly waste."""

    def __init__(self, region: str):
        """
        Initialize the Unused Resource Finder

        Args:
            region: AWS region to scan
        """
        self.ec2 = boto3.client("ec2", region_name=region)
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.rds = boto3.client("rds", region_name=region)
        self.region = region

    def _max_metric(
        self,
        namespace: str,
        metric_name: str,
        dimensions: List[Dict],
        days: int,
        statistic: str = "Average",
    ) -> Optional[float]:
        """Return the max of daily datapoints for a metric, or None if no data."""
        response = self.cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=datetime.now(timezone.utc) - timedelta(days=days),
            EndTime=datetime.now(timezone.utc),
            Period=86400,  # daily datapoints
            Statistics=[statistic],
        )
        datapoints = response.get("Datapoints", [])
        if not datapoints:
            return None
        return max(dp[statistic] for dp in datapoints)

    def find_idle_ec2_instances(self, cpu_threshold: float = 5.0, days: int = 14) -> List[Dict]:
        """
        Find EC2 instances whose CPU never exceeded the threshold.

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

                    max_daily_cpu = self._max_metric(
                        "AWS/EC2",
                        "CPUUtilization",
                        [{"Name": "InstanceId", "Value": instance_id}],
                        days,
                    )
                    if max_daily_cpu is None or max_daily_cpu >= cpu_threshold:
                        continue

                    idle_instances.append({
                        "InstanceId": instance_id,
                        "InstanceType": instance["InstanceType"],
                        "Region": self.region,
                        "Finding": "Idle EC2 Instance",
                        "Metric": f"Max of daily-average CPU over {days}d",
                        "Value": f"{max_daily_cpu:.2f}%",
                        "EstimatedMonthlySavingsUSD": None,
                        "Recommendation": (
                            "Review with the owner: stop, downsize, or put on a "
                            "start/stop schedule. Savings equal the instance's "
                            "compute price — quantify via cost_analysis.py "
                            "grouped by INSTANCE_TYPE."
                        ),
                    })
        return idle_instances

    def find_unattached_ebs_volumes(self) -> List[Dict]:
        """
        Find EBS volumes that are not attached to any instance

        Returns:
            List of unattached EBS volumes with estimated monthly cost
        """
        unattached_volumes = []
        paginator = self.ec2.get_paginator("describe_volumes")
        pages = paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}])

        for page in pages:
            for volume in page["Volumes"]:
                volume_type = volume.get("VolumeType", "gp3")
                size_gb = volume["Size"]
                gb_month = PRICING["ebs_gb_month"].get(volume_type, PRICING["ebs_gb_month"]["gp3"])
                unattached_volumes.append({
                    "VolumeId": volume["VolumeId"],
                    "VolumeType": volume_type,
                    "SizeGiB": size_gb,
                    "Region": self.region,
                    "Finding": "Unattached EBS Volume",
                    "EstimatedMonthlySavingsUSD": round(size_gb * gb_month, 2),
                    "Recommendation": "Snapshot then delete the volume, or reattach it",
                })
        return unattached_volumes

    def find_unused_elastic_ips(self) -> List[Dict]:
        """
        Find Elastic IPs that are not associated with any instance

        Returns:
            List of unused Elastic IPs with estimated monthly cost
        """
        unused_eips = []
        addresses = self.ec2.describe_addresses()

        for address in addresses["Addresses"]:
            if "InstanceId" not in address and "NetworkInterfaceId" not in address:
                unused_eips.append({
                    "PublicIp": address["PublicIp"],
                    "AllocationId": address.get("AllocationId", "N/A"),
                    "Region": self.region,
                    "Finding": "Unused Elastic IP",
                    "EstimatedMonthlySavingsUSD": PRICING["elastic_ip_month"],
                    "Recommendation": "Release the Elastic IP",
                })
        return unused_eips

    def find_old_ebs_snapshots(self, retention_days: int = 30) -> List[Dict]:
        """
        Find old EBS snapshots that exceed retention period. Snapshots tagged
        'Retain' (any value) are skipped, matching the cleanup Lambda's contract.

        Args:
            retention_days: Number of days to retain snapshots (default: 30)

        Returns:
            List of old EBS snapshots with estimated monthly cost
        """
        old_snapshots = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        owner_id = boto3.client("sts").get_caller_identity()["Account"]
        paginator = self.ec2.get_paginator("describe_snapshots")

        for page in paginator.paginate(OwnerIds=[owner_id]):
            for snapshot in page["Snapshots"]:
                if any(tag.get("Key") == "Retain" for tag in snapshot.get("Tags", [])):
                    continue
                if snapshot["StartTime"] >= cutoff:
                    continue

                size_gb = snapshot.get("VolumeSize", 0)
                old_snapshots.append({
                    "SnapshotId": snapshot["SnapshotId"],
                    "VolumeId": snapshot.get("VolumeId", "N/A"),
                    "SizeGiB": size_gb,
                    "StartTime": snapshot["StartTime"].isoformat(),
                    "Region": self.region,
                    "Finding": "Old EBS Snapshot",
                    # Upper bound: snapshots are incremental, so actual billed
                    # storage is usually below full volume size.
                    "EstimatedMonthlySavingsUSD": round(size_gb * PRICING["snapshot_gb_month"], 2),
                    "Recommendation": f"Delete snapshot (older than {retention_days} days) unless tagged Retain",
                })
        return old_snapshots

    def find_idle_rds_instances(self, days: int = 14) -> List[Dict]:
        """
        Find RDS instances with zero database connections over the window.

        Args:
            days: Number of days to analyze (default: 14)

        Returns:
            List of idle RDS instances
        """
        idle_rds = []
        paginator = self.rds.get_paginator("describe_db_instances")

        for page in paginator.paginate():
            for db in page["DBInstances"]:
                if db.get("DBInstanceStatus") != "available":
                    continue
                db_id = db["DBInstanceIdentifier"]

                max_connections = self._max_metric(
                    "AWS/RDS",
                    "DatabaseConnections",
                    [{"Name": "DBInstanceIdentifier", "Value": db_id}],
                    days,
                    statistic="Maximum",
                )
                if max_connections is None or max_connections > 0:
                    continue

                idle_rds.append({
                    "DBInstanceIdentifier": db_id,
                    "DBInstanceClass": db.get("DBInstanceClass", "unknown"),
                    "Engine": db.get("Engine", "unknown"),
                    "Region": self.region,
                    "Finding": "Idle RDS Instance",
                    "Metric": f"Max DatabaseConnections over {days}d",
                    "Value": "0",
                    "EstimatedMonthlySavingsUSD": None,
                    "Recommendation": (
                        "No connections in the analysis window. Review with the "
                        "owner: snapshot and stop (stoppable engines), or delete "
                        "after a final snapshot."
                    ),
                })
        return idle_rds

    def scan_all(
        self,
        cpu_threshold: float = 5.0,
        ec2_days: int = 14,
        snapshot_days: int = 30,
    ) -> Dict[str, List]:
        """
        Run all scans for unused resources

        Args:
            cpu_threshold: CPU threshold for idle instances
            ec2_days: Number of days to analyze for idle instances/RDS
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
            "IdleRDSInstances": self.find_idle_rds_instances(ec2_days),
        }
        print("Scan complete.")
        return results


def build_summary(all_results: Dict[str, List]) -> Dict:
    """Build a findings summary with total estimable monthly savings."""
    total_savings = 0.0
    unquantified = 0
    for findings in all_results.values():
        for finding in findings:
            savings = finding.get("EstimatedMonthlySavingsUSD")
            if savings is None:
                unquantified += 1
            else:
                total_savings += savings

    return {
        "TotalFindings": sum(len(v) for v in all_results.values()),
        "FindingsByType": {k: len(v) for k, v in all_results.items()},
        "EstimatedMonthlySavingsUSD": round(total_savings, 2),
        "UnquantifiedFindings": unquantified,
        "PricingAssumptions": (
            "us-east-1 on-demand list prices; snapshots costed at full volume "
            "size (upper bound). Idle EC2/RDS compute savings are not "
            "quantified here — see each finding's recommendation."
        ),
    }


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
    else:
        ec2 = boto3.client("ec2", region_name="us-east-1")
        regions = [r["RegionName"] for r in ec2.describe_regions()["Regions"]]

    all_results: Dict[str, List] = {
        "IdleEC2Instances": [],
        "UnattachedEBSVolumes": [],
        "UnusedElasticIPs": [],
        "OldEBSSnapshots": [],
        "IdleRDSInstances": [],
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
        except (ClientError, BotoCoreError) as e:
            print(f"Error scanning region {region}: {e}", file=sys.stderr)

    summary = build_summary(all_results)
    output = {"Summary": summary, **all_results}

    print(f"\nFindings: {summary['TotalFindings']} | "
          f"Estimated monthly savings (quantified findings): "
          f"${summary['EstimatedMonthlySavingsUSD']:,.2f}")

    # Export results to JSON
    try:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to {args.output}")
    except OSError as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
