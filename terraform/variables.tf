# AWS FinOps Cost Optimizer - Terraform Variables

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "aws-finops-optimizer"
}

variable "owner_email" {
  description = "Email address of the project owner"
  type        = string
}

variable "alert_email" {
  description = "Email address for cost alerts and notifications"
  type        = string
  default     = ""
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD (0 to disable)"
  type        = number
  default     = 0
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
  
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

variable "enable_auto_tagging" {
  description = "Enable automatic resource tagging Lambda function"
  type        = bool
  default     = true
}

variable "enable_scheduler" {
  description = "Enable EC2 instance scheduler Lambda function"
  type        = bool
  default     = true
}

variable "enable_snapshot_cleanup" {
  description = "Enable EBS snapshot cleanup Lambda function"
  type        = bool
  default     = true
}

variable "snapshot_retention_days" {
  description = "Number of days to retain EBS snapshots"
  type        = number
  default     = 30
}

variable "default_tags" {
  description = "Default tags to apply to untagged resources"
  type        = map(string)
  default = {
    Environment = "Untagged"
    Owner       = "Unknown"
    CostCenter  = "Unallocated"
  }
}
