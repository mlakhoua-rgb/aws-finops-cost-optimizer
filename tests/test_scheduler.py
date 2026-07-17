"""
Unit tests for lambda/scheduler/main.py
"""
import json
from unittest.mock import MagicMock, patch

from tests.lambda_loader import load_lambda_module

scheduler = load_lambda_module("scheduler", "scheduler_main")


def _paginator_with_instances(instance_ids):
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"Reservations": [{"Instances": [{"InstanceId": iid} for iid in instance_ids]}]}
    ]
    return paginator


class TestLambdaHandler:

    def test_rejects_invalid_action(self):
        result = scheduler.lambda_handler({"action": "reboot"}, None)
        assert result["statusCode"] == 400
        assert "Invalid action" in json.loads(result["body"])["Error"]

    def test_rejects_missing_action(self):
        result = scheduler.lambda_handler({}, None)
        assert result["statusCode"] == 400

    def test_stop_action(self, monkeypatch):
        monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)
        ec2 = MagicMock()
        ec2.get_paginator.return_value = _paginator_with_instances(["i-1", "i-2"])
        with patch.object(scheduler.boto3, "client", return_value=ec2):
            result = scheduler.lambda_handler({"action": "stop"}, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["AffectedInstances"] == ["i-1", "i-2"]
        ec2.stop_instances.assert_called_once_with(InstanceIds=["i-1", "i-2"])


class TestApplyAction:

    def test_stop_targets_running_instances(self):
        ec2 = MagicMock()
        ec2.get_paginator.return_value = _paginator_with_instances(["i-1"])
        affected = scheduler.apply_action(ec2, "stop", "AutoScheduler", "enabled")
        assert affected == ["i-1"]
        filters = ec2.get_paginator.return_value.paginate.call_args.kwargs["Filters"]
        state_filter = next(f for f in filters if f["Name"] == "instance-state-name")
        assert state_filter["Values"] == ["running"]
        ec2.stop_instances.assert_called_once()
        ec2.start_instances.assert_not_called()

    def test_start_targets_stopped_instances(self):
        ec2 = MagicMock()
        ec2.get_paginator.return_value = _paginator_with_instances(["i-9"])
        affected = scheduler.apply_action(ec2, "start", "AutoScheduler", "enabled")
        assert affected == ["i-9"]
        filters = ec2.get_paginator.return_value.paginate.call_args.kwargs["Filters"]
        state_filter = next(f for f in filters if f["Name"] == "instance-state-name")
        assert state_filter["Values"] == ["stopped"]
        ec2.start_instances.assert_called_once_with(InstanceIds=["i-9"])

    def test_no_matching_instances_makes_no_calls(self):
        ec2 = MagicMock()
        ec2.get_paginator.return_value = _paginator_with_instances([])
        affected = scheduler.apply_action(ec2, "stop", "AutoScheduler", "enabled")
        assert affected == []
        ec2.stop_instances.assert_not_called()

    def test_tag_filter_uses_configured_key_and_value(self):
        ec2 = MagicMock()
        ec2.get_paginator.return_value = _paginator_with_instances([])
        scheduler.apply_action(ec2, "stop", "Schedule", "office-hours")
        filters = ec2.get_paginator.return_value.paginate.call_args.kwargs["Filters"]
        tag_filter = next(f for f in filters if f["Name"] == "tag:Schedule")
        assert tag_filter["Values"] == ["office-hours"]


class TestPublishSummary:

    def test_skips_without_topic(self, monkeypatch):
        monkeypatch.delenv("SNS_TOPIC_ARN", raising=False)
        with patch.object(scheduler.boto3, "client") as client:
            scheduler.publish_summary({"Action": "stop", "Count": 2})
        client.assert_not_called()

    def test_skips_empty_run(self, monkeypatch):
        monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123:topic")
        with patch.object(scheduler.boto3, "client") as client:
            scheduler.publish_summary({"Action": "stop", "Count": 0})
        client.assert_not_called()

    def test_publishes_when_configured(self, monkeypatch):
        monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123:topic")
        sns = MagicMock()
        with patch.object(scheduler.boto3, "client", return_value=sns):
            scheduler.publish_summary({"Action": "stop", "AffectedInstances": ["i-1"], "Count": 1})
        sns.publish.assert_called_once()
        assert "stop" in sns.publish.call_args.kwargs["Subject"]

    def test_sns_failure_does_not_raise(self, monkeypatch):
        monkeypatch.setenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123:topic")
        sns = MagicMock()
        sns.publish.side_effect = RuntimeError("sns down")
        with patch.object(scheduler.boto3, "client", return_value=sns):
            scheduler.publish_summary({"Action": "stop", "Count": 1})
