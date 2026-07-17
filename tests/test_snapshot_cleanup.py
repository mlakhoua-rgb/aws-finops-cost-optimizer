"""
Unit tests for lambda/snapshot_cleanup/main.py
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from tests.lambda_loader import load_lambda_module

snapshot_cleanup = load_lambda_module("snapshot_cleanup", "snapshot_cleanup_main")

ACCOUNT = "123456789012"


def _snapshot(snapshot_id, age_days, tags=None):
    return {
        "SnapshotId": snapshot_id,
        "StartTime": datetime.now(timezone.utc) - timedelta(days=age_days),
        "Tags": tags or [],
    }


def _ec2_with_snapshots(snapshots):
    ec2 = MagicMock()
    ec2.get_paginator.return_value.paginate.return_value = [{"Snapshots": snapshots}]
    return ec2


class TestCleanupSnapshots:

    def test_dry_run_reports_but_never_deletes(self):
        ec2 = _ec2_with_snapshots([_snapshot("snap-old", age_days=45)])
        deleted = snapshot_cleanup.cleanup_snapshots(ec2, ACCOUNT, 30, dry_run=True)
        assert deleted == ["snap-old"]
        ec2.delete_snapshot.assert_not_called()

    def test_deletes_old_snapshot_when_not_dry_run(self):
        ec2 = _ec2_with_snapshots([_snapshot("snap-old", age_days=45)])
        deleted = snapshot_cleanup.cleanup_snapshots(ec2, ACCOUNT, 30, dry_run=False)
        assert deleted == ["snap-old"]
        ec2.delete_snapshot.assert_called_once_with(SnapshotId="snap-old")

    def test_recent_snapshot_kept(self):
        ec2 = _ec2_with_snapshots([_snapshot("snap-new", age_days=5)])
        deleted = snapshot_cleanup.cleanup_snapshots(ec2, ACCOUNT, 30, dry_run=False)
        assert deleted == []
        ec2.delete_snapshot.assert_not_called()

    def test_retain_tag_always_respected(self):
        ec2 = _ec2_with_snapshots([
            _snapshot("snap-keep", age_days=400, tags=[{"Key": "Retain", "Value": "true"}])
        ])
        deleted = snapshot_cleanup.cleanup_snapshots(ec2, ACCOUNT, 30, dry_run=False)
        assert deleted == []
        ec2.delete_snapshot.assert_not_called()

    def test_scopes_scan_to_account_snapshots(self):
        ec2 = _ec2_with_snapshots([])
        snapshot_cleanup.cleanup_snapshots(ec2, ACCOUNT, 30, dry_run=True)
        assert ec2.get_paginator.return_value.paginate.call_args.kwargs["OwnerIds"] == [ACCOUNT]

    def test_in_use_snapshot_error_does_not_stop_the_run(self):
        ec2 = _ec2_with_snapshots([
            _snapshot("snap-ami", age_days=45),
            _snapshot("snap-free", age_days=45),
        ])
        ec2.delete_snapshot.side_effect = [
            ClientError({"Error": {"Code": "InvalidSnapshot.InUse"}}, "DeleteSnapshot"),
            {},
        ]
        deleted = snapshot_cleanup.cleanup_snapshots(ec2, ACCOUNT, 30, dry_run=False)
        assert deleted == ["snap-free"]
