# AWS FinOps Cost Optimizer - Lambda Module
# Deploys the three automation Lambdas (auto-tagger, EC2 scheduler, snapshot
# cleanup) with their EventBridge triggers and log groups.
# License: MIT

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

# Note: AWS_REGION is NOT set in any environment block below — it is a
# reserved Lambda variable that the runtime provides; setting it makes
# the deployment fail with InvalidParameterValueException.

# --- Auto-Tagger Lambda ---

data "archive_file" "auto_tagger" {
  count       = var.enable_auto_tagging ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/auto_tagger"
  output_path = "${path.module}/../../../lambda/auto_tagger.zip"
}

resource "aws_lambda_function" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  function_name = "${var.project_name}-auto-tagger"
  role          = var.lambda_role_arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  filename         = data.archive_file.auto_tagger[0].output_path
  source_code_hash = data.archive_file.auto_tagger[0].output_base64sha256

  environment {
    variables = {
      DEFAULT_TAGS  = jsonencode(var.default_tags)
      SNS_TOPIC_ARN = var.sns_topic_arn
    }
  }

  tags = var.common_tags
}

resource "aws_cloudwatch_log_group" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  name              = "/aws/lambda/${aws_lambda_function.auto_tagger[0].function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.common_tags
}

resource "aws_cloudwatch_event_rule" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  name                = "${var.project_name}-auto-tagger-rule"
  description         = "Run auto-tagger Lambda function hourly"
  schedule_expression = "rate(1 hour)"
  tags                = var.common_tags
}

resource "aws_cloudwatch_event_target" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  rule      = aws_cloudwatch_event_rule.auto_tagger[0].name
  target_id = "AutoTaggerLambda"
  arn       = aws_lambda_function.auto_tagger[0].arn
}

resource "aws_lambda_permission" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auto_tagger[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.auto_tagger[0].arn
}

# --- EC2 Scheduler Lambda ---
# Two EventBridge rules invoke the same function: one sends {"action":"stop"}
# in the evening, one sends {"action":"start"} in the morning. Instances opt
# in with the tag <scheduler_tag_key>=<scheduler_tag_value>.

data "archive_file" "scheduler" {
  count       = var.enable_scheduler ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/scheduler"
  output_path = "${path.module}/../../../lambda/scheduler.zip"
}

resource "aws_lambda_function" "scheduler" {
  count = var.enable_scheduler ? 1 : 0

  function_name = "${var.project_name}-scheduler"
  role          = var.lambda_role_arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60

  filename         = data.archive_file.scheduler[0].output_path
  source_code_hash = data.archive_file.scheduler[0].output_base64sha256

  environment {
    variables = {
      TAG_KEY       = var.scheduler_tag_key
      TAG_VALUE     = var.scheduler_tag_value
      SNS_TOPIC_ARN = var.sns_topic_arn
    }
  }

  tags = var.common_tags
}

resource "aws_cloudwatch_log_group" "scheduler" {
  count = var.enable_scheduler ? 1 : 0

  name              = "/aws/lambda/${aws_lambda_function.scheduler[0].function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.common_tags
}

resource "aws_cloudwatch_event_rule" "scheduler_stop" {
  count = var.enable_scheduler ? 1 : 0

  name                = "${var.project_name}-scheduler-stop"
  description         = "Stop opted-in EC2 instances outside business hours"
  schedule_expression = var.scheduler_stop_schedule
  tags                = var.common_tags
}

resource "aws_cloudwatch_event_target" "scheduler_stop" {
  count = var.enable_scheduler ? 1 : 0

  rule      = aws_cloudwatch_event_rule.scheduler_stop[0].name
  target_id = "SchedulerStopLambda"
  arn       = aws_lambda_function.scheduler[0].arn
  input     = jsonencode({ action = "stop" })
}

resource "aws_cloudwatch_event_rule" "scheduler_start" {
  count = var.enable_scheduler ? 1 : 0

  name                = "${var.project_name}-scheduler-start"
  description         = "Start opted-in EC2 instances for business hours"
  schedule_expression = var.scheduler_start_schedule
  tags                = var.common_tags
}

resource "aws_cloudwatch_event_target" "scheduler_start" {
  count = var.enable_scheduler ? 1 : 0

  rule      = aws_cloudwatch_event_rule.scheduler_start[0].name
  target_id = "SchedulerStartLambda"
  arn       = aws_lambda_function.scheduler[0].arn
  input     = jsonencode({ action = "start" })
}

resource "aws_lambda_permission" "scheduler_stop" {
  count = var.enable_scheduler ? 1 : 0

  statement_id  = "AllowStopRuleFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scheduler_stop[0].arn
}

resource "aws_lambda_permission" "scheduler_start" {
  count = var.enable_scheduler ? 1 : 0

  statement_id  = "AllowStartRuleFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scheduler_start[0].arn
}

# --- Snapshot Cleanup Lambda ---

data "archive_file" "snapshot_cleanup" {
  count       = var.enable_snapshot_cleanup ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/snapshot_cleanup"
  output_path = "${path.module}/../../../lambda/snapshot_cleanup.zip"
}

resource "aws_lambda_function" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  function_name = "${var.project_name}-snapshot-cleanup"
  role          = var.lambda_role_arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  filename         = data.archive_file.snapshot_cleanup[0].output_path
  source_code_hash = data.archive_file.snapshot_cleanup[0].output_base64sha256

  environment {
    variables = {
      RETENTION_DAYS = tostring(var.snapshot_retention_days)
      DRY_RUN        = var.snapshot_dry_run ? "true" : "false"
      SNS_TOPIC_ARN  = var.sns_topic_arn
    }
  }

  tags = var.common_tags
}

resource "aws_cloudwatch_log_group" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  name              = "/aws/lambda/${aws_lambda_function.snapshot_cleanup[0].function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.common_tags
}

resource "aws_cloudwatch_event_rule" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  name                = "${var.project_name}-snapshot-cleanup-rule"
  description         = "Run snapshot cleanup Lambda function daily"
  schedule_expression = "cron(0 4 * * ? *)" # Daily at 4am UTC
  tags                = var.common_tags
}

resource "aws_cloudwatch_event_target" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  rule      = aws_cloudwatch_event_rule.snapshot_cleanup[0].name
  target_id = "SnapshotCleanupLambda"
  arn       = aws_lambda_function.snapshot_cleanup[0].arn
}

resource "aws_lambda_permission" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.snapshot_cleanup[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.snapshot_cleanup[0].arn
}
