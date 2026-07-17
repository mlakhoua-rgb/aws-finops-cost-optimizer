# AWS FinOps Cost Optimizer - Main Terraform Configuration
# License: MIT

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state management
  # Uncomment and configure for production use
  # backend "s3" {
  #   bucket         = "your-terraform-state-bucket"
  #   key            = "finops/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AWS-FinOps-Cost-Optimizer"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Owner       = var.owner_email
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local variables
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  common_tags = {
    Project     = "AWS-FinOps-Cost-Optimizer"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ---------------------------------------------------------------------------
# S3 bucket for cost reports
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "finops_reports" {
  bucket = "${var.project_name}-reports-${local.account_id}"

  tags = merge(
    local.common_tags,
    {
      Name = "FinOps Cost Reports"
    }
  )
}

resource "aws_s3_bucket_versioning" "finops_reports" {
  bucket = aws_s3_bucket.finops_reports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "finops_reports" {
  bucket = aws_s3_bucket.finops_reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "finops_reports" {
  bucket = aws_s3_bucket.finops_reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# The cost tool should not hoard storage itself: expire aged reports and
# clean up noncurrent versions and failed uploads.
resource "aws_s3_bucket_lifecycle_configuration" "finops_reports" {
  bucket = aws_s3_bucket.finops_reports.id

  rule {
    id     = "expire-old-reports"
    status = "Enabled"

    filter {}

    expiration {
      days = var.report_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ---------------------------------------------------------------------------
# SNS topic for cost alerts and automation run summaries
# ---------------------------------------------------------------------------

resource "aws_sns_topic" "cost_alerts" {
  name              = "${var.project_name}-cost-alerts"
  display_name      = "FinOps Cost Alerts"
  kms_master_key_id = "alias/aws/sns"

  tags = merge(
    local.common_tags,
    {
      Name = "FinOps Cost Alerts"
    }
  )
}

resource "aws_sns_topic_subscription" "cost_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------------------------------------------------------------------------
# IAM role for the automation Lambdas — least privilege: only the actions
# the three functions actually perform.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda_execution" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logging"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${var.project_name}-*"
      },
      {
        Sid    = "ReadResources"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots"
        ]
        Resource = "*"
      },
      {
        Sid    = "OptimizationActions"
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:CreateTags",
          "ec2:DeleteSnapshot"
        ]
        Resource = "*"
      },
      {
        Sid      = "Notifications"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.cost_alerts.arn
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Automation Lambdas (auto-tagger, EC2 scheduler, snapshot cleanup)
# ---------------------------------------------------------------------------

module "lambda" {
  source = "./modules/lambda"

  project_name    = var.project_name
  lambda_role_arn = aws_iam_role.lambda_execution.arn
  common_tags     = local.common_tags
  sns_topic_arn   = aws_sns_topic.cost_alerts.arn

  log_retention_days = var.log_retention_days

  enable_auto_tagging = var.enable_auto_tagging
  default_tags        = var.default_tags

  enable_scheduler         = var.enable_scheduler
  scheduler_stop_schedule  = var.scheduler_stop_schedule
  scheduler_start_schedule = var.scheduler_start_schedule

  enable_snapshot_cleanup = var.enable_snapshot_cleanup
  snapshot_retention_days = var.snapshot_retention_days
  snapshot_dry_run        = var.snapshot_dry_run
}

# ---------------------------------------------------------------------------
# AWS Budget — actual and forecasted alerts
# ---------------------------------------------------------------------------

resource "aws_budgets_budget" "monthly_cost" {
  count = var.monthly_budget_limit > 0 ? 1 : 0

  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  # Fixed past date: using timestamp() here causes a perpetual plan diff.
  time_period_start = "2024-01-01_00:00"
  time_unit         = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_email != "" ? [var.alert_email] : []
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_email != "" ? [var.alert_email] : []
  }

  # Early warning: alert when the month-end forecast exceeds the budget,
  # before the money is actually spent.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alert_email != "" ? [var.alert_email] : []
  }
}

# ---------------------------------------------------------------------------
# Cost Anomaly Detection — ML-based spend anomaly alerts per service
# ---------------------------------------------------------------------------

resource "aws_ce_anomaly_monitor" "service" {
  name              = "${var.project_name}-service-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"

  tags = local.common_tags
}

resource "aws_ce_anomaly_subscription" "alerts" {
  count = var.alert_email != "" ? 1 : 0

  name             = "${var.project_name}-anomaly-alerts"
  frequency        = "DAILY"
  monitor_arn_list = [aws_ce_anomaly_monitor.service.arn]

  subscriber {
    type    = "EMAIL"
    address = var.alert_email
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = [tostring(var.anomaly_threshold_usd)]
    }
  }

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "s3_bucket_name" {
  description = "S3 bucket for cost reports"
  value       = aws_s3_bucket.finops_reports.id
}

output "sns_topic_arn" {
  description = "SNS topic ARN for cost alerts"
  value       = aws_sns_topic.cost_alerts.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for Lambda functions"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_function_names" {
  description = "Deployed automation Lambda function names"
  value = compact([
    module.lambda.auto_tagger_function_name,
    module.lambda.scheduler_function_name,
    module.lambda.snapshot_cleanup_function_name,
  ])
}

output "anomaly_monitor_arn" {
  description = "Cost Anomaly Detection monitor ARN"
  value       = aws_ce_anomaly_monitor.service.arn
}
