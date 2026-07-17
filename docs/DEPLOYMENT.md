# AWS FinOps Cost Optimizer — Deployment Guide

Step-by-step instructions for deploying the toolkit with Terraform.

## Prerequisites

- **AWS account** with permissions to create IAM roles, Lambda functions, EventBridge rules, S3 buckets, SNS topics, budgets, and Cost Explorer anomaly monitors.
- **AWS CLI** configured (`aws configure` or environment variables).
- **Terraform** ≥ 1.6.0.
- **Python** 3.11+ (only needed for running the analysis scripts).

## Step 1: Clone the repository

```bash
git clone https://github.com/mlakhoua-rgb/aws-finops-cost-optimizer.git
cd aws-finops-cost-optimizer
```

## Step 2 (recommended): Configure a remote state backend

For anything beyond a personal sandbox, store Terraform state remotely:

```bash
aws s3 mb s3://your-terraform-state-bucket-name
aws s3api put-bucket-versioning --bucket your-terraform-state-bucket-name \
  --versioning-configuration Status=Enabled
```

Then uncomment and fill in the `backend "s3"` block in `terraform/main.tf`.

## Step 3: Configure variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`. The one required variable is `owner_email`; the ones worth thinking about:

| Variable | Effect | Default |
|---|---|---|
| `alert_email` | Receives budget alerts, anomaly alerts, and automation run summaries. Empty string disables email. | `""` |
| `monthly_budget_limit` | USD budget; alerts at 80%/100% actual and 100% forecasted. 0 disables. | `0` |
| `anomaly_threshold_usd` | Minimum anomaly impact that triggers an alert | `10` |
| `scheduler_stop_schedule` / `scheduler_start_schedule` | UTC cron pair for the EC2 scheduler | weekdays 19:00 / 07:00 |
| `snapshot_retention_days` | Snapshot age threshold for cleanup | `30` |
| `snapshot_dry_run` | Keep `true` until you've reviewed dry-run reports | `true` |

## Step 4: Deploy

```bash
terraform init
terraform plan    # review what will be created
terraform apply
```

Outputs include the report bucket name, SNS topic ARN, and deployed Lambda function names.

## Step 5: Confirm subscriptions and verify

1. **Confirm the SNS email subscription** — check `alert_email`'s inbox for the AWS confirmation link (alerts don't flow until confirmed).
2. **Lambda console** — the three functions (`<project_name>-auto-tagger`, `-scheduler`, `-snapshot-cleanup`) exist with EventBridge triggers attached.
3. **Smoke-test the scheduler contract** — tag a disposable instance `AutoScheduler=enabled`, then invoke the scheduler manually:
   ```bash
   aws lambda invoke --function-name aws-finops-optimizer-scheduler \
     --payload '{"action": "stop"}' --cli-binary-format raw-in-base64-out /dev/stdout
   ```
4. **Snapshot cleanup dry run** — invoke it and read the log output; nothing is deleted while `DRY_RUN=true`.

## Step 6: Import the CloudWatch dashboard

Billing metrics only exist in us-east-1 and require **Receive Billing Alerts** to be enabled in Billing preferences:

```bash
aws cloudwatch put-dashboard --dashboard-name FinOps-Overview \
  --dashboard-body file://../dashboards/cost_overview_dashboard.json --region us-east-1
```

## Step 7: Run the analysis scripts

```bash
cd ../
pip install -r scripts/requirements.txt

python scripts/cost_analysis.py --days 30 --group-by SERVICE --output report.csv
python scripts/unused_resources.py --region us-east-1 --output unused.json
python scripts/commitment_coverage.py --days 30 --output commitments.json
```

## Enabling destructive cleanup (deliberate step)

After several dry-run reports look right:

1. Set `snapshot_dry_run = false` in `terraform.tfvars`.
2. `terraform apply`.
3. Watch the next daily run's SNS summary; snapshots tagged `Retain` are always preserved.

## Destroying the infrastructure

```bash
cd terraform
terraform destroy
```

**Warning:** irreversible; also deletes the report bucket contents. The Terraform-managed resources are only the toolkit itself — your workload resources are never managed here.
