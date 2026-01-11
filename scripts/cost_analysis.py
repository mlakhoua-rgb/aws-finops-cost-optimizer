#!/usr/bin/env python3
"""
AWS Cost Analysis Script

This script queries AWS Cost Explorer API to generate detailed cost reports
by service, region, account, or custom tags. It provides visibility into
spending patterns and helps identify cost optimization opportunities.

Usage:
    python cost_analysis.py --days 30 --group-by SERVICE --output report.csv

Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
License: MIT
"""

import argparse
import boto3
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys


class CostAnalyzer:
    """AWS Cost Explorer analysis tool"""

    def __init__(self, region: str = "us-east-1"):
        """
        Initialize the Cost Analyzer
        
        Args:
            region: AWS region for Cost Explorer API (default: us-east-1)
        """
        self.client = boto3.client('ce', region_name=region)
        
    def get_cost_and_usage(
        self,
        start_date: str,
        end_date: str,
        granularity: str = "MONTHLY",
        group_by: Optional[List[Dict]] = None,
        metrics: List[str] = None
    ) -> Dict:
        """
        Query AWS Cost Explorer API for cost and usage data
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            granularity: DAILY, MONTHLY, or HOURLY
            group_by: List of grouping dimensions (e.g., SERVICE, REGION)
            metrics: List of metrics to retrieve (default: UnblendedCost)
            
        Returns:
            Dict containing cost and usage data
        """
        if metrics is None:
            metrics = ["UnblendedCost"]
            
        params = {
            "TimePeriod": {
                "Start": start_date,
                "End": end_date
            },
            "Granularity": granularity,
            "Metrics": metrics
        }
        
        if group_by:
            params["GroupBy"] = group_by
            
        try:
            response = self.client.get_cost_and_usage(**params)
            return response
        except Exception as e:
            print(f"Error querying Cost Explorer: {e}", file=sys.stderr)
            sys.exit(1)
    
    def analyze_costs(
        self,
        days: int = 30,
        group_by_dimension: str = "SERVICE"
    ) -> List[Dict]:
        """
        Analyze costs for the specified time period
        
        Args:
            days: Number of days to analyze (default: 30)
            group_by_dimension: Dimension to group by (SERVICE, REGION, etc.)
            
        Returns:
            List of cost records with service/region and cost information
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Query Cost Explorer
        group_by = [{"Type": "DIMENSION", "Key": group_by_dimension}]
        response = self.get_cost_and_usage(
            start_date=start_str,
            end_date=end_str,
            granularity="MONTHLY",
            group_by=group_by
        )
        
        # Parse results
        cost_records = []
        for result in response.get("ResultsByTime", []):
            period_start = result["TimePeriod"]["Start"]
            period_end = result["TimePeriod"]["End"]
            
            for group in result.get("Groups", []):
                dimension_value = group["Keys"][0]
                cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                
                cost_records.append({
                    "PeriodStart": period_start,
                    "PeriodEnd": period_end,
                    "Dimension": group_by_dimension,
                    "Value": dimension_value,
                    "Cost": round(cost, 2),
                    "Currency": group["Metrics"]["UnblendedCost"]["Unit"]
                })
        
        # Sort by cost descending
        cost_records.sort(key=lambda x: x["Cost"], reverse=True)
        
        return cost_records
    
    def calculate_total_cost(self, cost_records: List[Dict]) -> float:
        """Calculate total cost from cost records"""
        return sum(record["Cost"] for record in cost_records)
    
    def calculate_percentage(self, cost_records: List[Dict]) -> List[Dict]:
        """Add percentage of total cost to each record"""
        total_cost = self.calculate_total_cost(cost_records)
        
        if total_cost == 0:
            return cost_records
        
        for record in cost_records:
            record["Percentage"] = round((record["Cost"] / total_cost) * 100, 2)
        
        return cost_records
    
    def export_to_csv(self, cost_records: List[Dict], filename: str):
        """
        Export cost records to CSV file
        
        Args:
            cost_records: List of cost records
            filename: Output CSV filename
        """
        if not cost_records:
            print("No cost data to export", file=sys.stderr)
            return
        
        fieldnames = cost_records[0].keys()
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(cost_records)
            
            print(f"Cost report exported to {filename}")
        except Exception as e:
            print(f"Error writing CSV file: {e}", file=sys.stderr)
            sys.exit(1)
    
    def export_to_json(self, cost_records: List[Dict], filename: str):
        """
        Export cost records to JSON file
        
        Args:
            cost_records: List of cost records
            filename: Output JSON filename
        """
        try:
            with open(filename, 'w') as jsonfile:
                json.dump(cost_records, jsonfile, indent=2)
            
            print(f"Cost report exported to {filename}")
        except Exception as e:
            print(f"Error writing JSON file: {e}", file=sys.stderr)
            sys.exit(1)
    
    def print_summary(self, cost_records: List[Dict], top_n: int = 10):
        """
        Print a summary of costs to console
        
        Args:
            cost_records: List of cost records
            top_n: Number of top items to display
        """
        if not cost_records:
            print("No cost data available")
            return
        
        total_cost = self.calculate_total_cost(cost_records)
        
        print("\n" + "="*80)
        print(f"AWS Cost Analysis Summary")
        print("="*80)
        print(f"Total Cost: ${total_cost:,.2f} {cost_records[0]['Currency']}")
        print(f"Period: {cost_records[0]['PeriodStart']} to {cost_records[0]['PeriodEnd']}")
        print(f"Group By: {cost_records[0]['Dimension']}")
        print(f"\nTop {top_n} Cost Items:")
        print("-"*80)
        print(f"{'Rank':<6} {'Item':<40} {'Cost':<15} {'Percentage':<10}")
        print("-"*80)
        
        for idx, record in enumerate(cost_records[:top_n], 1):
            print(f"{idx:<6} {record['Value']:<40} ${record['Cost']:>12,.2f} {record.get('Percentage', 0):>8.2f}%")
        
        print("="*80 + "\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Analyze AWS costs using Cost Explorer API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze costs for last 30 days by service
  python cost_analysis.py --days 30 --group-by SERVICE --output report.csv
  
  # Analyze costs by region for last 90 days
  python cost_analysis.py --days 90 --group-by REGION --output regional_costs.json
  
  # Quick summary for last 7 days
  python cost_analysis.py --days 7 --group-by SERVICE
        """
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze (default: 30)"
    )
    
    parser.add_argument(
        "--group-by",
        type=str,
        default="SERVICE",
        choices=["SERVICE", "REGION", "USAGE_TYPE", "INSTANCE_TYPE"],
        help="Dimension to group costs by (default: SERVICE)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file (CSV or JSON based on extension)"
    )
    
    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region for Cost Explorer API (default: us-east-1)"
    )
    
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top items to display in summary (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = CostAnalyzer(region=args.region)
    
    # Analyze costs
    print(f"Analyzing AWS costs for the last {args.days} days...")
    cost_records = analyzer.analyze_costs(
        days=args.days,
        group_by_dimension=args.group_by
    )
    
    # Add percentage calculations
    cost_records = analyzer.calculate_percentage(cost_records)
    
    # Print summary
    analyzer.print_summary(cost_records, top_n=args.top)
    
    # Export if output file specified
    if args.output:
        if args.output.endswith('.csv'):
            analyzer.export_to_csv(cost_records, args.output)
        elif args.output.endswith('.json'):
            analyzer.export_to_json(cost_records, args.output)
        else:
            print("Error: Output file must have .csv or .json extension", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
