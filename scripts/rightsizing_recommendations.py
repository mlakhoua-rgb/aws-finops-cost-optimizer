#!/usr/bin/env python3
"""
AWS EC2 Right-Sizing Recommendations Script

Analyses EC2 instance utilisation metrics (CPU via AWS/EC2, memory via
CloudWatch Agent custom metrics) and produces right-sizing recommendations.

Memory metrics require the CloudWatch Agent to be installed and configured
on target instances with the standard CWAgent namespace. If the agent is not
present on an instance, that instance is analysed on CPU only and the memory
field is reported as "N/A (CW Agent not installed)".

Usage:
    python rightsizing_recommendations.py --region eu-west-1 --output recs.json
    python rightsizing_recommendations.py --region us-east-1 --days 30 --cpu-threshold 50 --output recs.json

Author: Mohamed Ben Lakhoua
License: MIT
"""

import argparse
import boto3
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import sys


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CW_AGENT_NAMESPACE = "CWAgent"
CW_AGENT_MEM_METRIC = "mem_used_percent"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _max_metric(
    cloudwatch,
    namespace: str,
    metric_name: str,
    dimensions: List[Dict],
    start: datetime,
    end: datetime,
    period: int = 3600,
) -> Optional[float]:
    """
    Return the maximum value of a CloudWatch metric over the given window.
    Returns None if no data points are available.
    """
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start,
        EndTime=end,
        Period=period,
        Statistics=["Maximum"],
    )
    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return None
    return max(dp["Maximum"] for dp in datapoints)


def _get_memory_utilisation(
    cloudwatch,
    instance_id: str,
    start: datetime,
    end: datetime,
) -> Tuple[Optional[float], str]:
    """
    Query memory utilisation from the CloudWatch Agent namespace.

    Returns (value_or_None, status_string).
    Status is one of:
      - "cw_agent"        — real data from CloudWatch Agent
      - "no_cw_agent"     — no data found; agent likely not installed
    """
    dims = [{"Name": "InstanceId", "Value": instance_id}]
    value = _max_metric(
        cloudwatch, CW_AGENT_NAMESPACE, CW_AGENT_MEM_METRIC, dims, start, end
    )
    if value is not None:
        return value, "cw_agent"
    return None, "no_cw_agent"


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------

class RightSizingRecommender:
    """Produces right-sizing recommendations for EC2 instances."""

    def __init__(self, region: str):
        self.ec2 = boto3.client("ec2", region_name=region)
        self.cloudwatch = boto3.client("cloudwatch", region_name=region)
        self.region = region

    def get_recommendations(
        self,
        days: int = 14,
        cpu_threshold: float = 40.0,
        mem_threshold: float = 40.0,
    ) -> List[Dict]:
        """
        Scan running EC2 instances and return a list of right-sizing findings.

        An instance is flagged when:
          • CPU max < cpu_threshold  AND
          • Memory max < mem_threshold  (if CloudWatch Agent data is available)
          OR
          • CPU max < cpu_threshold  (when no CW Agent data is present — flagged
            with a note that memory could not be evaluated)

        Args:
            days:           Look-back window in days.
            cpu_threshold:  Flag instance when max CPU% is below this value.
            mem_threshold:  Flag instance when max mem% is below this value
                            (only applied when CW Agent data is available).

        Returns:
            List of recommendation dicts.
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        recommendations: List[Dict] = []
        paginator = self.ec2.get_paginator("describe_instances")
        pages = paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        for page in pages:
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]
                    instance_type = instance["InstanceType"]
                    name_tag = next(
                        (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                        instance_id,
                    )

                    # --- CPU ---
                    max_cpu = _max_metric(
                        self.cloudwatch,
                        "AWS/EC2",
                        "CPUUtilization",
                        [{"Name": "InstanceId", "Value": instance_id}],
                        start,
                        end,
                    )
                    if max_cpu is None:
                        # No CPU data — instance may be brand new or not reporting
                        continue

                    # --- Memory ---
                    max_mem, mem_status = _get_memory_utilisation(
                        self.cloudwatch, instance_id, start, end
                    )

                    # --- Decision logic ---
                    cpu_over_provisioned = max_cpu < cpu_threshold

                    if mem_status == "cw_agent":
                        mem_over_provisioned = max_mem < mem_threshold  # type: ignore[operator]
                        flagged = cpu_over_provisioned and mem_over_provisioned
                        mem_display = f"{max_mem:.1f}%"
                        mem_note = ""
                    else:
                        # No agent data — flag on CPU alone but make it clear
                        flagged = cpu_over_provisioned
                        mem_display = "N/A"
                        mem_note = (
                            "Memory data unavailable — CloudWatch Agent not detected "
                            "on this instance. Install the agent for full analysis."
                        )

                    if not flagged:
                        continue

                    rec = {
                        "InstanceId": instance_id,
                        "InstanceName": name_tag,
                        "InstanceType": instance_type,
                        "Region": self.region,
                        "AnalysisPeriodDays": days,
                        "Finding": "Potentially over-provisioned",
                        "MaxCPUPercent": round(max_cpu, 2),
                        "MaxMemoryPercent": mem_display,
                        "MemoryDataSource": mem_status,
                        "Recommendation": (
                            f"Consider a smaller instance in the same family "
                            f"(current: {instance_type}). Validate with application "
                            f"owner before resizing."
                        ),
                    }
                    if mem_note:
                        rec["MemoryNote"] = mem_note

                    recommendations.append(rec)

        return recommendations


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate EC2 right-sizing recommendations using CloudWatch metrics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Requirements:
  • IAM permissions: ec2:DescribeInstances, cloudwatch:GetMetricStatistics
  • For memory analysis: CloudWatch Agent installed on target instances

Examples:
  python rightsizing_recommendations.py --region eu-west-1 --output recs.json
  python rightsizing_recommendations.py --region us-east-1 --days 30 --cpu-threshold 50 --output recs.json
        """,
    )
    parser.add_argument("--region", required=True, help="AWS region to scan")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--days", type=int, default=14, help="Look-back window in days (default: 14)")
    parser.add_argument("--cpu-threshold", type=float, default=40.0,
                        help="Flag instances with max CPU%% below this value (default: 40.0)")
    parser.add_argument("--mem-threshold", type=float, default=40.0,
                        help="Flag instances with max memory%% below this value (default: 40.0, requires CW Agent)")

    args = parser.parse_args()

    print(f"Scanning {args.region} — last {args.days} days …")
    recommender = RightSizingRecommender(region=args.region)
    recommendations = recommender.get_recommendations(
        days=args.days,
        cpu_threshold=args.cpu_threshold,
        mem_threshold=args.mem_threshold,
    )

    try:
        with open(args.output, "w") as f:
            json.dump(recommendations, f, indent=2)
        print(f"✅ {len(recommendations)} recommendation(s) written to {args.output}")
    except OSError as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
