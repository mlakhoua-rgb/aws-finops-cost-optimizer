"""
Unit tests for commitment_coverage.py
"""
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from commitment_coverage import CommitmentAnalyzer


def _data_unavailable(operation):
    return ClientError({"Error": {"Code": "DataUnavailableException"}}, operation)


def _analyzer():
    a = CommitmentAnalyzer.__new__(CommitmentAnalyzer)
    a.client = MagicMock()
    return a


class TestSavingsPlansUtilization:

    def test_parses_totals(self):
        analyzer = _analyzer()
        analyzer.client.get_savings_plans_utilization.return_value = {
            "Total": {
                "Utilization": {
                    "UtilizationPercentage": "97.5",
                    "UnusedCommitment": "12.30",
                },
                "Savings": {"NetSavings": "450.00"},
            }
        }
        result = analyzer.savings_plans_utilization(days=30)
        assert result == {
            "UtilizationPercentage": 97.5,
            "UnusedCommitmentUSD": 12.30,
            "NetSavingsUSD": 450.00,
        }

    def test_no_savings_plans_returns_none(self):
        analyzer = _analyzer()
        analyzer.client.get_savings_plans_utilization.side_effect = _data_unavailable(
            "GetSavingsPlansUtilization"
        )
        assert analyzer.savings_plans_utilization(days=30) is None

    def test_other_client_errors_propagate(self):
        analyzer = _analyzer()
        analyzer.client.get_savings_plans_utilization.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException"}}, "GetSavingsPlansUtilization"
        )
        try:
            analyzer.savings_plans_utilization(days=30)
            assert False, "expected ClientError"
        except ClientError:
            pass


class TestSavingsPlansCoverage:

    def test_averages_monthly_coverage(self):
        analyzer = _analyzer()
        analyzer.client.get_savings_plans_coverage.return_value = {
            "SavingsPlansCoverages": [
                {"Coverage": {"CoveragePercentage": "40.0", "OnDemandCost": "600"}},
                {"Coverage": {"CoveragePercentage": "60.0", "OnDemandCost": "400"}},
            ]
        }
        result = analyzer.savings_plans_coverage(days=60)
        assert result["AverageCoveragePercentage"] == 50.0
        assert result["UncoveredOnDemandCostUSD"] == 1000.0

    def test_empty_response_returns_none(self):
        analyzer = _analyzer()
        analyzer.client.get_savings_plans_coverage.return_value = {
            "SavingsPlansCoverages": []
        }
        assert analyzer.savings_plans_coverage(days=30) is None


class TestReservations:

    def test_parses_ri_utilization(self):
        analyzer = _analyzer()
        analyzer.client.get_reservation_utilization.return_value = {
            "Total": {
                "UtilizationPercentage": "88.2",
                "UnusedHours": "120",
                "NetRISavings": "300.50",
            }
        }
        result = analyzer.reservation_utilization(days=30)
        assert result["UtilizationPercentage"] == 88.2
        assert result["UnusedHours"] == 120.0

    def test_parses_ri_coverage(self):
        analyzer = _analyzer()
        analyzer.client.get_reservation_coverage.return_value = {
            "Total": {"CoverageHours": {
                "CoverageHoursPercentage": "72.0",
                "OnDemandHours": "500",
                "ReservedHours": "1300",
            }}
        }
        result = analyzer.reservation_coverage(days=30)
        assert result["CoverageHoursPercentage"] == 72.0

    def test_empty_totals_return_none(self):
        analyzer = _analyzer()
        analyzer.client.get_reservation_utilization.return_value = {"Total": {}}
        analyzer.client.get_reservation_coverage.return_value = {"Total": {}}
        assert analyzer.reservation_utilization(days=30) is None
        assert analyzer.reservation_coverage(days=30) is None


class TestObservations:

    def test_low_utilization_flagged(self):
        report = {
            "SavingsPlans": {
                "Utilization": {"UtilizationPercentage": 80.0, "UnusedCommitmentUSD": 200.0},
                "Coverage": None,
            },
            "ReservedInstances": {"Utilization": None, "Coverage": None},
        }
        observations = CommitmentAnalyzer._observations(report)
        assert any("80.0%" in o for o in observations)

    def test_no_commitments_recommends_modelling(self):
        report = {
            "SavingsPlans": {"Utilization": None, "Coverage": None},
            "ReservedInstances": {"Utilization": None, "Coverage": None},
        }
        observations = CommitmentAnalyzer._observations(report)
        assert any("No Savings Plans or Reserved Instances" in o for o in observations)

    def test_healthy_report_says_so(self):
        report = {
            "SavingsPlans": {
                "Utilization": {"UtilizationPercentage": 99.0, "UnusedCommitmentUSD": 1.0},
                "Coverage": {"AverageCoveragePercentage": 85.0, "UncoveredOnDemandCostUSD": 50.0},
            },
            "ReservedInstances": {
                "Utilization": {"UtilizationPercentage": 98.0, "UnusedHours": 2.0,
                                "NetRISavingsUSD": 100.0},
                "Coverage": {"CoverageHoursPercentage": 90.0, "OnDemandHours": 10.0,
                             "ReservedHours": 90.0},
            },
        }
        observations = CommitmentAnalyzer._observations(report)
        assert observations == [
            "Commitment utilization and coverage look healthy for this period."
        ]
