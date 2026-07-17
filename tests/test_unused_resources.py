"""
Unit tests for unused_resources.py
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from unused_resources import PRICING, UnusedResourceFinder, build_summary


def _finder():
    f = UnusedResourceFinder.__new__(UnusedResourceFinder)
    f.ec2 = MagicMock()
    f.cloudwatch = MagicMock()
    f.rds = MagicMock()
    f.region = "us-east-1"
    return f


def _datapoints(values, statistic="Average"):
    return {"Datapoints": [{statistic: v} for v in values]}


class TestIdleEC2:

    def _with_instance(self, finder, cpu_datapoints):
        finder.ec2.get_paginator.return_value.paginate.return_value = [
            {"Reservations": [{"Instances": [
                {"InstanceId": "i-1", "InstanceType": "t3.medium"}
            ]}]}
        ]
        finder.cloudwatch.get_metric_statistics.return_value = _datapoints(cpu_datapoints)

    def test_flags_idle_instance(self):
        finder = _finder()
        self._with_instance(finder, [1.0, 2.5, 0.8])
        findings = finder.find_idle_ec2_instances(cpu_threshold=5.0, days=14)
        assert len(findings) == 1
        assert findings[0]["InstanceId"] == "i-1"
        assert findings[0]["EstimatedMonthlySavingsUSD"] is None

    def test_busy_instance_not_flagged(self):
        finder = _finder()
        self._with_instance(finder, [1.0, 60.0])
        assert finder.find_idle_ec2_instances(cpu_threshold=5.0, days=14) == []

    def test_no_metrics_not_flagged(self):
        finder = _finder()
        self._with_instance(finder, [])
        assert finder.find_idle_ec2_instances() == []


class TestUnattachedVolumes:

    def test_savings_use_volume_type_price(self):
        finder = _finder()
        finder.ec2.get_paginator.return_value.paginate.return_value = [
            {"Volumes": [{"VolumeId": "vol-1", "VolumeType": "gp2", "Size": 100}]}
        ]
        findings = finder.find_unattached_ebs_volumes()
        assert len(findings) == 1
        expected = round(100 * PRICING["ebs_gb_month"]["gp2"], 2)
        assert findings[0]["EstimatedMonthlySavingsUSD"] == expected

    def test_unknown_volume_type_falls_back_to_gp3_price(self):
        finder = _finder()
        finder.ec2.get_paginator.return_value.paginate.return_value = [
            {"Volumes": [{"VolumeId": "vol-1", "VolumeType": "future-type", "Size": 10}]}
        ]
        findings = finder.find_unattached_ebs_volumes()
        assert findings[0]["EstimatedMonthlySavingsUSD"] == round(
            10 * PRICING["ebs_gb_month"]["gp3"], 2
        )


class TestUnusedElasticIPs:

    def test_only_unassociated_addresses_flagged(self):
        finder = _finder()
        finder.ec2.describe_addresses.return_value = {
            "Addresses": [
                {"PublicIp": "1.1.1.1", "AllocationId": "eip-1", "InstanceId": "i-1"},
                {"PublicIp": "2.2.2.2", "AllocationId": "eip-2"},
            ]
        }
        findings = finder.find_unused_elastic_ips()
        assert len(findings) == 1
        assert findings[0]["PublicIp"] == "2.2.2.2"
        assert findings[0]["EstimatedMonthlySavingsUSD"] == PRICING["elastic_ip_month"]


class TestOldSnapshots:

    def _with_snapshots(self, finder, snapshots):
        finder.ec2.get_paginator.return_value.paginate.return_value = [
            {"Snapshots": snapshots}
        ]

    def test_old_snapshot_flagged_with_savings(self):
        finder = _finder()
        self._with_snapshots(finder, [{
            "SnapshotId": "snap-1",
            "VolumeSize": 40,
            "StartTime": datetime.now(timezone.utc) - timedelta(days=90),
        }])
        with patch("unused_resources.boto3.client") as client:
            client.return_value.get_caller_identity.return_value = {"Account": "123"}
            findings = finder.find_old_ebs_snapshots(retention_days=30)
        assert len(findings) == 1
        assert findings[0]["EstimatedMonthlySavingsUSD"] == round(
            40 * PRICING["snapshot_gb_month"], 2
        )

    def test_retain_tag_skipped(self):
        finder = _finder()
        self._with_snapshots(finder, [{
            "SnapshotId": "snap-1",
            "VolumeSize": 40,
            "StartTime": datetime.now(timezone.utc) - timedelta(days=90),
            "Tags": [{"Key": "Retain", "Value": "compliance"}],
        }])
        with patch("unused_resources.boto3.client") as client:
            client.return_value.get_caller_identity.return_value = {"Account": "123"}
            findings = finder.find_old_ebs_snapshots(retention_days=30)
        assert findings == []


class TestIdleRDS:

    def _with_db(self, finder, connection_datapoints, status="available"):
        finder.rds.get_paginator.return_value.paginate.return_value = [
            {"DBInstances": [{
                "DBInstanceIdentifier": "db-1",
                "DBInstanceClass": "db.t3.medium",
                "Engine": "postgres",
                "DBInstanceStatus": status,
            }]}
        ]
        finder.cloudwatch.get_metric_statistics.return_value = _datapoints(
            connection_datapoints, statistic="Maximum"
        )

    def test_zero_connections_flagged(self):
        finder = _finder()
        self._with_db(finder, [0.0, 0.0, 0.0])
        findings = finder.find_idle_rds_instances(days=14)
        assert len(findings) == 1
        assert findings[0]["DBInstanceIdentifier"] == "db-1"

    def test_active_database_not_flagged(self):
        finder = _finder()
        self._with_db(finder, [0.0, 12.0])
        assert finder.find_idle_rds_instances(days=14) == []

    def test_stopped_database_not_scanned(self):
        finder = _finder()
        self._with_db(finder, [0.0], status="stopped")
        assert finder.find_idle_rds_instances(days=14) == []


class TestBuildSummary:

    def test_totals_and_unquantified_count(self):
        summary = build_summary({
            "UnattachedEBSVolumes": [
                {"EstimatedMonthlySavingsUSD": 8.0},
                {"EstimatedMonthlySavingsUSD": 2.5},
            ],
            "IdleEC2Instances": [{"EstimatedMonthlySavingsUSD": None}],
        })
        assert summary["TotalFindings"] == 3
        assert summary["EstimatedMonthlySavingsUSD"] == 10.5
        assert summary["UnquantifiedFindings"] == 1
        assert summary["FindingsByType"]["UnattachedEBSVolumes"] == 2
