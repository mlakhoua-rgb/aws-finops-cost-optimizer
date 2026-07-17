#!/usr/bin/env python3
"""
AWS Commitment Coverage & Utilization Script

Reports Savings Plans and Reserved Instance utilization and coverage from the
Cost Explorer API — the rate-optimization side of FinOps that complements the
usage-optimization scripts in this toolkit:

  * Utilization — of the commitments already purchased, how much is being
    used? Low utilization means paying for capacity nothing consumes
    (over-commitment).
  * Coverage — of the eligible on-demand spend, how much is covered by a
    commitment? Low coverage with steady usage usually means money is left
    on the table at on-demand rates.

Both numbers are reported raw; purchase decisions need workload context
(steady vs. spiky, growth plans, upcoming migrations) and belong to a human.

Usage:
    python commitment_coverage.py --days 30 --output commitments.json

Author: Mohamed Ben Lakhoua
License: MIT
"""

import argparse
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import sys


class CommitmentAnalyzer:
    """Savings Plans / Reserved Instance utilization and coverage reporting."""

    def __init__(self, region: str = "us-east-1"):
        # Cost Explorer is a global API served from us-east-1.
        self.client = boto3.client("ce", region_name=region)

    def _time_period(self, days: int) -> Dict[str, str]:
        end = datetime.now().date()
        start = end - timedelta(days=days)
        return {"Start": start.strftime("%Y-%m-%d"), "End": end.strftime("%Y-%m-%d")}

    def _call(self, description: str, fn, **kwargs) -> Optional[Dict]:
        """
        Call a Cost Explorer API, returning None when the account simply has
        no data for it (no Savings Plans / no RIs) instead of failing.
        """
        try:
            return fn(**kwargs)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "DataUnavailableException":
                print(f"  {description}: no data (none purchased or Cost Explorer not ready)")
                return None
            raise

    def savings_plans_utilization(self, days: int) -> Optional[Dict]:
        """Return overall Savings Plans utilization for the window."""
        response = self._call(
            "Savings Plans utilization",
            self.client.get_savings_plans_utilization,
            TimePeriod=self._time_period(days),
        )
        if response is None:
            return None
        total = response.get("Total", {})
        utilization = total.get("Utilization", {})
        savings = total.get("Savings", {})
        return {
            "UtilizationPercentage": round(float(utilization.get("UtilizationPercentage", 0)), 2),
            "UnusedCommitmentUSD": round(float(utilization.get("UnusedCommitment", 0)), 2),
            "NetSavingsUSD": round(float(savings.get("NetSavings", 0)), 2),
        }

    def savings_plans_coverage(self, days: int) -> Optional[Dict]:
        """Return average Savings Plans coverage of eligible spend."""
        response = self._call(
            "Savings Plans coverage",
            self.client.get_savings_plans_coverage,
            TimePeriod=self._time_period(days),
            Granularity="MONTHLY",
        )
        if response is None:
            return None
        coverages = response.get("SavingsPlansCoverages", [])
        if not coverages:
            return None
        percentages = [
            float(c.get("Coverage", {}).get("CoveragePercentage", 0)) for c in coverages
        ]
        on_demand = sum(
            float(c.get("Coverage", {}).get("OnDemandCost", 0)) for c in coverages
        )
        return {
            "AverageCoveragePercentage": round(sum(percentages) / len(percentages), 2),
            "UncoveredOnDemandCostUSD": round(on_demand, 2),
        }

    def reservation_utilization(self, days: int) -> Optional[Dict]:
        """Return overall Reserved Instance utilization for the window."""
        response = self._call(
            "Reserved Instance utilization",
            self.client.get_reservation_utilization,
            TimePeriod=self._time_period(days),
        )
        if response is None:
            return None
        total = response.get("Total", {})
        if not total:
            return None
        return {
            "UtilizationPercentage": round(float(total.get("UtilizationPercentage", 0)), 2),
            "UnusedHours": round(float(total.get("UnusedHours", 0)), 2),
            "NetRISavingsUSD": round(float(total.get("NetRISavings", 0)), 2),
        }

    def reservation_coverage(self, days: int) -> Optional[Dict]:
        """Return overall Reserved Instance coverage for the window."""
        response = self._call(
            "Reserved Instance coverage",
            self.client.get_reservation_coverage,
            TimePeriod=self._time_period(days),
        )
        if response is None:
            return None
        coverage_hours = response.get("Total", {}).get("CoverageHours", {})
        if not coverage_hours:
            return None
        return {
            "CoverageHoursPercentage": round(
                float(coverage_hours.get("CoverageHoursPercentage", 0)), 2
            ),
            "OnDemandHours": round(float(coverage_hours.get("OnDemandHours", 0)), 2),
            "ReservedHours": round(float(coverage_hours.get("ReservedHours", 0)), 2),
        }

    def build_report(self, days: int) -> Dict:
        """Run all four analyses and assemble a report with observations."""
        report: Dict = {
            "AnalysisPeriodDays": days,
            "SavingsPlans": {
                "Utilization": self.savings_plans_utilization(days),
                "Coverage": self.savings_plans_coverage(days),
            },
            "ReservedInstances": {
                "Utilization": self.reservation_utilization(days),
                "Coverage": self.reservation_coverage(days),
            },
        }
        report["Observations"] = self._observations(report)
        return report

    @staticmethod
    def _observations(report: Dict) -> list:
        """Derive plain-language observations. Thresholds are conventions, not rules."""
        observations = []

        sp_util = report["SavingsPlans"]["Utilization"]
        if sp_util and sp_util["UtilizationPercentage"] < 95:
            observations.append(
                f"Savings Plans utilization is {sp_util['UtilizationPercentage']}% — "
                f"${sp_util['UnusedCommitmentUSD']} of commitment went unused this "
                "period. Investigate before renewing or adding commitments."
            )

        sp_cov = report["SavingsPlans"]["Coverage"]
        if sp_cov and sp_cov["AverageCoveragePercentage"] < 60:
            observations.append(
                f"Savings Plans coverage averages {sp_cov['AverageCoveragePercentage']}% — "
                f"${sp_cov['UncoveredOnDemandCostUSD']} of eligible spend ran at "
                "on-demand rates. If this usage is steady, model a commitment purchase."
            )

        ri_util = report["ReservedInstances"]["Utilization"]
        if ri_util and ri_util["UtilizationPercentage"] < 95:
            observations.append(
                f"RI utilization is {ri_util['UtilizationPercentage']}% "
                f"({ri_util['UnusedHours']} unused hours). Check for instance-family "
                "drift or consider selling/exchanging convertible RIs."
            )

        if not any(
            section[key]
            for section in (report["SavingsPlans"], report["ReservedInstances"])
            for key in section
        ):
            observations.append(
                "No Savings Plans or Reserved Instances found. If on-demand usage "
                "is steady, commitment discounts (typically 20-72%) are the largest "
                "single rate-optimization lever available."
            )

        if not observations:
            observations.append(
                "Commitment utilization and coverage look healthy for this period."
            )
        return observations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report Savings Plans / Reserved Instance utilization and coverage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Requirements:
  IAM: ce:GetSavingsPlansUtilization, ce:GetSavingsPlansCoverage,
       ce:GetReservationUtilization, ce:GetReservationCoverage

Examples:
  python commitment_coverage.py --days 30 --output commitments.json
  python commitment_coverage.py --days 90
        """,
    )
    parser.add_argument("--days", type=int, default=30,
                        help="Look-back window in days (default: 30)")
    parser.add_argument("--output", type=str,
                        help="Optional output JSON file")
    args = parser.parse_args()

    print(f"Analyzing commitment coverage for the last {args.days} days...")
    analyzer = CommitmentAnalyzer()
    try:
        report = analyzer.build_report(days=args.days)
    except (ClientError, BotoCoreError) as e:
        print(f"Error querying Cost Explorer: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(report, indent=2))

    if args.output:
        try:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to {args.output}")
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
