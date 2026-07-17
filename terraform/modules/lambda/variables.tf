# AWS FinOps Cost Optimizer - Lambda Module Variables

variable "project_name" {
  description = "Project name used as a prefix for resource naming"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN assumed by the Lambda functions"
  type        = string
}

variable "common_tags" {
  description = "Tags applied to all module resources"
  type        = map(string)
  default     = {}
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for run summaries (empty string disables notifications)"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention for Lambda log groups"
  type        = number
  default     = 30
}

# --- Auto-tagger ---

variable "enable_auto_tagging" {
  description = "Deploy the auto-tagger Lambda function"
  type        = bool
  default     = true
}

variable "default_tags" {
  description = "Tag key/value pairs the auto-tagger applies when missing"
  type        = map(string)
  default = {
    Environment = "Untagged"
    Owner       = "Unknown"
    CostCenter  = "Unallocated"
  }
}

# --- EC2 scheduler ---

variable "enable_scheduler" {
  description = "Deploy the EC2 start/stop scheduler Lambda function"
  type        = bool
  default     = true
}

variable "scheduler_tag_key" {
  description = "Tag key that opts an instance into scheduling"
  type        = string
  default     = "AutoScheduler"
}

variable "scheduler_tag_value" {
  description = "Tag value that opts an instance into scheduling"
  type        = string
  default     = "enabled"
}

variable "scheduler_stop_schedule" {
  description = "EventBridge schedule expression for stopping instances (UTC)"
  type        = string
  default     = "cron(0 19 ? * MON-FRI *)"
}

variable "scheduler_start_schedule" {
  description = "EventBridge schedule expression for starting instances (UTC)"
  type        = string
  default     = "cron(0 7 ? * MON-FRI *)"
}

# --- Snapshot cleanup ---

variable "enable_snapshot_cleanup" {
  description = "Deploy the EBS snapshot cleanup Lambda function"
  type        = bool
  default     = true
}

variable "snapshot_retention_days" {
  description = "Snapshots older than this many days are eligible for cleanup"
  type        = number
  default     = 30
}

variable "snapshot_dry_run" {
  description = "When true (default), snapshot cleanup only reports what it would delete"
  type        = bool
  default     = true
}
