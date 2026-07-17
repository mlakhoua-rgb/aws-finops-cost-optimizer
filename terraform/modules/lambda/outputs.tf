# AWS FinOps Cost Optimizer - Lambda Module Outputs

output "auto_tagger_function_name" {
  description = "Name of the auto-tagger Lambda function (null when disabled)"
  value       = var.enable_auto_tagging ? aws_lambda_function.auto_tagger[0].function_name : null
}

output "scheduler_function_name" {
  description = "Name of the EC2 scheduler Lambda function (null when disabled)"
  value       = var.enable_scheduler ? aws_lambda_function.scheduler[0].function_name : null
}

output "snapshot_cleanup_function_name" {
  description = "Name of the snapshot cleanup Lambda function (null when disabled)"
  value       = var.enable_snapshot_cleanup ? aws_lambda_function.snapshot_cleanup[0].function_name : null
}
