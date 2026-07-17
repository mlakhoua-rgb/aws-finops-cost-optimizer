"""
Unit tests for lambda/auto_tagger/main.py
"""
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from tests.lambda_loader import load_lambda_module

auto_tagger = load_lambda_module("auto_tagger", "auto_tagger_main")

DEFAULT_TAGS = {"Environment": "Untagged", "Owner": "Unknown"}


class TestApplyMissingTags:

    def test_adds_only_missing_keys(self):
        ec2 = MagicMock()
        added = auto_tagger.apply_missing_tags(ec2, "i-1", {"Environment"}, DEFAULT_TAGS)
        assert added is True
        tags = ec2.create_tags.call_args.kwargs["Tags"]
        assert tags == [{"Key": "Owner", "Value": "Unknown"}]

    def test_fully_tagged_resource_untouched(self):
        ec2 = MagicMock()
        added = auto_tagger.apply_missing_tags(
            ec2, "i-1", {"Environment", "Owner"}, DEFAULT_TAGS
        )
        assert added is False
        ec2.create_tags.assert_not_called()

    def test_client_error_does_not_raise(self):
        ec2 = MagicMock()
        ec2.create_tags.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation"}}, "CreateTags"
        )
        added = auto_tagger.apply_missing_tags(ec2, "i-1", set(), DEFAULT_TAGS)
        assert added is False


class TestTagUntaggedInstances:

    def _ec2_with_instances(self, instances):
        ec2 = MagicMock()
        ec2.get_paginator.return_value.paginate.return_value = [
            {"Reservations": [{"Instances": instances}]}
        ]
        return ec2

    def test_tags_untagged_instance(self):
        ec2 = self._ec2_with_instances([{"InstanceId": "i-1", "Tags": []}])
        tagged = auto_tagger.tag_untagged_instances(ec2, DEFAULT_TAGS)
        assert tagged == ["i-1"]
        ec2.create_tags.assert_called_once()

    def test_existing_tag_values_never_overwritten(self):
        ec2 = self._ec2_with_instances([
            {"InstanceId": "i-1", "Tags": [{"Key": "Environment", "Value": "prod"}]}
        ])
        auto_tagger.tag_untagged_instances(ec2, DEFAULT_TAGS)
        tags = ec2.create_tags.call_args.kwargs["Tags"]
        assert {"Key": "Environment", "Value": "Untagged"} not in tags
        assert {"Key": "Owner", "Value": "Unknown"} in tags

    def test_one_failure_does_not_stop_the_run(self):
        ec2 = self._ec2_with_instances([
            {"InstanceId": "i-bad", "Tags": []},
            {"InstanceId": "i-good", "Tags": []},
        ])
        ec2.create_tags.side_effect = [
            ClientError({"Error": {"Code": "InvalidID"}}, "CreateTags"),
            {},
        ]
        tagged = auto_tagger.tag_untagged_instances(ec2, DEFAULT_TAGS)
        assert tagged == ["i-good"]


class TestTagUntaggedVolumes:

    def test_tags_untagged_volume(self):
        ec2 = MagicMock()
        ec2.get_paginator.return_value.paginate.return_value = [
            {"Volumes": [{"VolumeId": "vol-1", "Tags": []}]}
        ]
        tagged = auto_tagger.tag_untagged_volumes(ec2, DEFAULT_TAGS)
        assert tagged == ["vol-1"]

    def test_fully_tagged_volume_skipped(self):
        ec2 = MagicMock()
        ec2.get_paginator.return_value.paginate.return_value = [
            {"Volumes": [{
                "VolumeId": "vol-1",
                "Tags": [{"Key": "Environment", "Value": "prod"},
                         {"Key": "Owner", "Value": "team-a"}],
            }]}
        ]
        tagged = auto_tagger.tag_untagged_volumes(ec2, DEFAULT_TAGS)
        assert tagged == []
        ec2.create_tags.assert_not_called()
