"""
Unit tests for cost_analysis.py
"""
from unittest.mock import MagicMock

from cost_analysis import CostAnalyzer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_CE_RESPONSE = {
    "ResultsByTime": [
        {
            "TimePeriod": {"Start": "2026-02-01", "End": "2026-03-01"},
            "Groups": [
                {
                    "Keys": ["Amazon EC2"],
                    "Metrics": {"UnblendedCost": {"Amount": "1500.50", "Unit": "USD"}},
                },
                {
                    "Keys": ["Amazon S3"],
                    "Metrics": {"UnblendedCost": {"Amount": "250.00", "Unit": "USD"}},
                },
                {
                    "Keys": ["AWS Lambda"],
                    "Metrics": {"UnblendedCost": {"Amount": "12.75", "Unit": "USD"}},
                },
            ],
        }
    ],
    "ResponseMetadata": {},
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCostAnalyzer:

    def setup_method(self):
        self.analyzer = CostAnalyzer(region="us-east-1")
        self.analyzer.client = MagicMock()
        self.analyzer.client.get_cost_and_usage.return_value = MOCK_CE_RESPONSE

    def test_analyze_costs_returns_sorted_list(self):
        records = self.analyzer.analyze_costs(days=30, group_by_dimension="SERVICE")
        assert isinstance(records, list)
        assert len(records) == 3
        # Should be sorted by cost descending
        costs = [r["Cost"] for r in records]
        assert costs == sorted(costs, reverse=True)

    def test_analyze_costs_correct_values(self):
        records = self.analyzer.analyze_costs(days=30)
        top = records[0]
        assert top["Value"] == "Amazon EC2"
        assert top["Cost"] == 1500.50
        assert top["Currency"] == "USD"

    def test_pagination_merges_all_pages(self):
        """Large accounts paginate via NextPageToken — all pages must be read."""
        page1 = {
            "ResultsByTime": [{
                "TimePeriod": {"Start": "2026-02-01", "End": "2026-03-01"},
                "Groups": [{
                    "Keys": ["Amazon EC2"],
                    "Metrics": {"UnblendedCost": {"Amount": "100.00", "Unit": "USD"}},
                }],
            }],
            "NextPageToken": "token-1",
        }
        page2 = {
            "ResultsByTime": [{
                "TimePeriod": {"Start": "2026-03-01", "End": "2026-04-01"},
                "Groups": [{
                    "Keys": ["Amazon S3"],
                    "Metrics": {"UnblendedCost": {"Amount": "50.00", "Unit": "USD"}},
                }],
            }],
        }
        self.analyzer.client.get_cost_and_usage.side_effect = [page1, page2]
        records = self.analyzer.analyze_costs(days=60)
        assert {r["Value"] for r in records} == {"Amazon EC2", "Amazon S3"}
        assert self.analyzer.client.get_cost_and_usage.call_count == 2
        second_call = self.analyzer.client.get_cost_and_usage.call_args_list[1]
        assert second_call.kwargs["NextPageToken"] == "token-1"

    def test_multi_period_costs_aggregate_per_service(self):
        """A window spanning two calendar months yields one row per service, summed."""
        response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2026-02-15", "End": "2026-03-01"},
                    "Groups": [{
                        "Keys": ["Amazon EC2"],
                        "Metrics": {"UnblendedCost": {"Amount": "100.00", "Unit": "USD"}},
                    }],
                },
                {
                    "TimePeriod": {"Start": "2026-03-01", "End": "2026-03-15"},
                    "Groups": [{
                        "Keys": ["Amazon EC2"],
                        "Metrics": {"UnblendedCost": {"Amount": "150.00", "Unit": "USD"}},
                    }],
                },
            ]
        }
        self.analyzer.client.get_cost_and_usage.return_value = response
        records = self.analyzer.analyze_costs(days=30)
        assert len(records) == 1
        assert records[0]["Cost"] == 250.00

    def test_calculate_total_cost(self):
        records = self.analyzer.analyze_costs(days=30)
        total = self.analyzer.calculate_total_cost(records)
        assert abs(total - 1763.25) < 0.01

    def test_calculate_percentage(self):
        records = self.analyzer.analyze_costs(days=30)
        records = self.analyzer.calculate_percentage(records)
        percentages = [r["Percentage"] for r in records]
        assert abs(sum(percentages) - 100.0) < 0.1
        assert all(0 <= p <= 100 for p in percentages)

    def test_calculate_percentage_zero_total(self):
        """Should return records unchanged when total cost is zero."""
        records = [{"Cost": 0.0}, {"Cost": 0.0}]
        result = self.analyzer.calculate_percentage(records)
        assert result == records

    def test_export_to_csv(self, tmp_path):
        records = self.analyzer.analyze_costs(days=30)
        records = self.analyzer.calculate_percentage(records)
        output = str(tmp_path / "test_report.csv")
        self.analyzer.export_to_csv(records, output)
        import csv
        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3
        assert rows[0]["Value"] == "Amazon EC2"

    def test_export_to_json(self, tmp_path):
        import json
        records = self.analyzer.analyze_costs(days=30)
        output = str(tmp_path / "test_report.json")
        self.analyzer.export_to_json(records, output)
        with open(output) as f:
            data = json.load(f)
        assert len(data) == 3

    def test_print_summary_no_crash(self, capsys):
        records = self.analyzer.analyze_costs(days=30)
        records = self.analyzer.calculate_percentage(records)
        self.analyzer.print_summary(records, top_n=2)
        captured = capsys.readouterr()
        assert "Amazon EC2" in captured.out
        assert "1,500.50" in captured.out

    def test_print_summary_empty(self, capsys):
        self.analyzer.print_summary([], top_n=5)
        captured = capsys.readouterr()
        assert "No cost data" in captured.out
