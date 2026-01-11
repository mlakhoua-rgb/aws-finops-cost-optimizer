# AWS FinOps Cost Optimizer - Main Terraform Configuration
# Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
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

# S3 bucket for cost reports and Lambda code
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

# SNS topic for cost alerts
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

# CloudWatch Log Group for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# IAM role for Lambda functions
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

# IAM policy for Lambda execution
resource "aws_iam_role_policy" "lambda_execution" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_execution.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
          "ec2:DescribeAddresses",
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:CreateTags",
          "ec2:DeleteSnapshot"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.finops_reports.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.cost_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Budget for cost monitoring
resource "aws_budgets_budget" "monthly_cost" {
  count = var.monthly_budget_limit > 0 ? 1 : 0
  
  name              = "${var.project_name}-monthly-budget"
  budget_type       = "COST"
  limit_amount      = var.monthly_budget_limit
  limit_unit        = "USD"
  time_period_start = formatdate("YYYY-MM-01_00:00", timestamp())
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
}

# Outputs
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
