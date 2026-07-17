# AWS FinOps Cost Optimizer — Troubleshooting

Common issues, their causes, and fixes.

## Analysis scripts

### `AccessDeniedException` when calling Cost Explorer

**Cause:** Cost Explorer is not enabled for the account, or the caller lacks `ce:Get*` permissions. In AWS Organizations, member accounts may be blocked from Cost Explorer by the management account's settings.

**Fix:** Enable Cost Explorer in the Billing console (one-time, per account) and attach a policy with the `ce:GetCostAndUsage`, `ce:GetSavingsPlansUtilization`, `ce:GetSavingsPlansCoverage`, `ce:GetReservationUtilization`, `ce:GetReservationCoverage` actions. For member accounts, check the management account's Cost Explorer preferences.

### Cost Explorer returns no data right after enabling it

**Cause:** first-time activation triggers a backfill that takes ~24 hours.

**Fix:** wait a day, then re-run. Historical data (up to 13 months) appears after backfill completes.

### `DataUnavailableException` from `commitment_coverage.py`

**Cause:** the account has never purchased Savings Plans or Reserved Instances — there is no data to report. The script treats this as a normal case and reports the sections as absent, with an observation instead of a crash. If you see the raw exception, you're on an old version.

### `rightsizing_recommendations.py` shows `MaxMemoryPercent: N/A`

**Cause:** memory metrics are not published by EC2 natively; they require the CloudWatch Agent on the instance publishing `mem_used_percent` to the `CWAgent` namespace.

**Fix:** install and configure the CloudWatch Agent on target instances, or accept CPU-only analysis (the finding says which basis was used).

### Idle checks return nothing for instances you know are idle

**Cause:** CloudWatch `get_metric_statistics` returns no datapoints for instances launched more recently than the analysis window, or the metric period exceeds the retention of detailed metrics.

**Fix:** shorten `--ec2-days`, or verify the instance has been running long enough to have daily datapoints.

## Terraform

### `InvalidParameterValueException: ... reserved key ... AWS_REGION` on `terraform apply`

**Cause:** something re-added `AWS_REGION` to a Lambda `environment` block. It is a reserved variable the Lambda runtime injects; user configuration cannot set it.

**Fix:** remove it. The functions read the region from the runtime-provided variable automatically.

### `terraform plan` always shows the budget changing

**Cause:** `time_period_start` derived from `timestamp()`, which changes every run.

**Fix:** already fixed here — the budget uses a fixed past date. If you forked an older version, replace `formatdate(..., timestamp())` with a literal like `"2024-01-01_00:00"`.

### Email subscriptions show `PendingConfirmation` forever

**Cause:** SNS email subscriptions and budget notifications require the recipient to click the confirmation link.

**Fix:** check the `alert_email` inbox (and spam) for "AWS Notification - Subscription Confirmation" and confirm it. Terraform cannot confirm on your behalf.

### `Error: creating CE Anomaly Subscription ... ValidationException`

**Cause:** usually an `anomaly_threshold_usd` of 0 or a malformed subscriber email.

**Fix:** set a positive threshold and a valid `alert_email`. To disable anomaly alerts entirely, set `alert_email = ""` (the subscription is count-gated on it).

## Lambda automation

### The scheduler never stops/starts anything

**Cause:** instances aren't opted in, or the tag doesn't match exactly.

**Fix:** tag instances with `AutoScheduler=enabled` (key and value are case-sensitive; both configurable via the module variables). Check the function's CloudWatch logs — it logs "nothing to stop/start" explicitly.

### Snapshot cleanup reports snapshots but never deletes them

**Cause:** working as designed — `DRY_RUN` defaults to `true`.

**Fix:** review a few dry-run reports first, then set `snapshot_dry_run = false` in `terraform.tfvars` and re-apply.

### Snapshot deletion fails with `InvalidSnapshot.InUse`

**Cause:** the snapshot backs a registered AMI.

**Fix:** expected; the function logs it and continues. Deregister the AMI first if the snapshot really should go.

## Dashboard

### Billing widgets are empty

**Cause:** `AWS/Billing` metrics are only published (a) in **us-east-1** and (b) when **Receive Billing Alerts** is enabled in Billing preferences.

**Fix:** enable billing alerts, and import/view the dashboard in us-east-1. Data appears within ~6 hours.

### Lambda widgets show no data

**Cause:** either the widget `FunctionName` dimensions assume the default `project_name` (`aws-finops-optimizer`), or the stack was deployed to a region other than us-east-1 — the Lambda widgets query the region set in the dashboard JSON, and Lambda metrics live in the deployment region (only billing metrics are inherently us-east-1).

**Fix:** update the function names and/or the two Lambda widgets' `region` in `dashboards/cost_overview_dashboard.json` before importing.

## Tests

### `pytest` fails with `ModuleNotFoundError: No module named 'boto3'`

**Fix:** install dev dependencies from the repo root: `pip install -r requirements-dev.txt`.

### Tests pass locally but flake8 fails in CI

**Fix:** run the exact CI invocation: `flake8 scripts/ lambda/ tests/ --max-line-length=120 --extend-ignore=E203`.
