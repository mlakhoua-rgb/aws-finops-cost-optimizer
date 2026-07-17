"""
Unit tests for rightsizing_recommendations.py
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from rightsizing_recommendations import (
    RightSizingRecommender,
    _get_memory_utilisation,
    _max_metric,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_instance(instance_id="i-abc123", instance_type="t3.large", name="test-server"):
    return {
        "InstanceId": instance_id,
        "InstanceType": instance_type,
        "Tags": [{"Key": "Name", "Value": name}],
    }


def _cw_response(values):
    """Build a mock CloudWatch get_metric_statistics response."""
    return {
        "Datapoints": [{"Maximum": v, "Timestamp": datetime.now(timezone.utc)} for v in values]
    }


# ---------------------------------------------------------------------------
# _max_metric
# ---------------------------------------------------------------------------

class TestMaxMetric:

    def test_returns_maximum(self):
        cw = MagicMock()
        cw.get_metric_statistics.return_value = _cw_response([10.0, 45.0, 30.0])
        result = _max_metric(cw, "AWS/EC2", "CPUUtilization", [], MagicMock(), MagicMock())
        assert result == 45.0

    def test_returns_none_when_no_datapoints(self):
        cw = MagicMock()
        cw.get_metric_statistics.return_value = {"Datapoints": []}
        result = _max_metric(cw, "AWS/EC2", "CPUUtilization", [], MagicMock(), MagicMock())
        assert result is None


# ---------------------------------------------------------------------------
# _get_memory_utilisation
# ---------------------------------------------------------------------------

class TestGetMemoryUtilisation:

    def test_returns_value_when_cw_agent_present(self):
        cw = MagicMock()
        cw.get_metric_statistics.return_value = _cw_response([55.0, 60.0])
        value, status = _get_memory_utilisation(cw, "i-abc123", MagicMock(), MagicMock())
        assert value == 60.0
        assert status == "cw_agent"

    def test_returns_none_when_no_agent(self):
        cw = MagicMock()
        cw.get_metric_statistics.return_value = {"Datapoints": []}
        value, status = _get_memory_utilisation(cw, "i-abc123", MagicMock(), MagicMock())
        assert value is None
        assert status == "no_cw_agent"


# ---------------------------------------------------------------------------
# RightSizingRecommender
# ---------------------------------------------------------------------------

class TestRightSizingRecommender:

    def _make_recommender(self, cpu_values, mem_values=None):
        """Create a recommender with mocked AWS clients."""
        r = RightSizingRecommender(region="eu-west-1")
        r.ec2 = MagicMock()
        r.cloudwatch = MagicMock()

        r.ec2.get_paginator.return_value.paginate.return_value = [
            {"Reservations": [{"Instances": [_make_instance()]}]}
        ]

        def cw_side_effect(**kwargs):
            if kwargs["Namespace"] == "AWS/EC2":
                return _cw_response(cpu_values)
            if mem_values is not None:
                return _cw_response(mem_values)
            return {"Datapoints": []}

        r.cloudwatch.get_metric_statistics.side_effect = cw_side_effect
        return r

    def test_flags_over_provisioned_with_cw_agent(self):
        r = self._make_recommender(cpu_values=[15.0, 20.0], mem_values=[25.0, 30.0])
        recs = r.get_recommendations(cpu_threshold=40.0, mem_threshold=40.0)
        assert len(recs) == 1
        assert recs[0]["InstanceId"] == "i-abc123"
        assert recs[0]["MemoryDataSource"] == "cw_agent"
        assert "MemoryNote" not in recs[0]

    def test_does_not_flag_high_cpu(self):
        r = self._make_recommender(cpu_values=[75.0, 80.0], mem_values=[25.0])
        recs = r.get_recommendations(cpu_threshold=40.0, mem_threshold=40.0)
        assert len(recs) == 0

    def test_does_not_flag_high_memory(self):
        r = self._make_recommender(cpu_values=[15.0], mem_values=[80.0, 85.0])
        recs = r.get_recommendations(cpu_threshold=40.0, mem_threshold=40.0)
        assert len(recs) == 0

    def test_flags_on_cpu_only_when_no_cw_agent(self):
        """When CW Agent is absent, instance should be flagged on CPU alone with a note."""
        r = self._make_recommender(cpu_values=[10.0, 15.0], mem_values=None)
        recs = r.get_recommendations(cpu_threshold=40.0, mem_threshold=40.0)
        assert len(recs) == 1
        assert recs[0]["MaxMemoryPercent"] == "N/A"
        assert recs[0]["MemoryDataSource"] == "no_cw_agent"
        assert "MemoryNote" in recs[0]
        assert "CloudWatch Agent" in recs[0]["MemoryNote"]

    def test_skips_instances_with_no_cpu_data(self):
        r = self._make_recommender(cpu_values=[])
        recs = r.get_recommendations()
        assert len(recs) == 0

    def test_recommendation_contains_required_fields(self):
        r = self._make_recommender(cpu_values=[5.0], mem_values=[10.0])
        recs = r.get_recommendations()
        assert len(recs) == 1
        rec = recs[0]
        for field in ["InstanceId", "InstanceName", "InstanceType", "Region",
                      "Finding", "MaxCPUPercent", "MaxMemoryPercent", "Recommendation"]:
            assert field in rec, f"Missing field: {field}"
