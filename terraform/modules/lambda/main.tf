# AWS FinOps Cost Optimizer - Lambda Module
# Author: Mohamed Ben Lakhoua (AI-Augmented with Manus AI)
# License: MIT

# --- Auto-Tagger Lambda ---
resource "aws_lambda_function" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  function_name = "${var.project_name}-auto-tagger"
  role          = var.lambda_role_arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  filename         = "${path.module}/../../lambda/auto_tagger.zip"
  source_code_hash = data.archive_file.auto_tagger[0].output_base64sha256

  environment {
    variables = {
      DEFAULT_TAGS = jsonencode(var.default_tags)
      AWS_REGION   = var.aws_region
    }
  }

  tags = var.common_tags
}

data "archive_file" "auto_tagger" {
  count       = var.enable_auto_tagging ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/auto_tagger"
  output_path = "${path.module}/../../lambda/auto_tagger.zip"
}

resource "aws_cloudwatch_event_rule" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  name                = "${var.project_name}-auto-tagger-rule"
  description         = "Run auto-tagger Lambda function hourly"
  schedule_expression = "rate(1 hour)"
}

resource "aws_cloudwatch_event_target" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  rule      = aws_cloudwatch_event_rule.auto_tagger[0].name
  target_id = "AutoTaggerLambda"
  arn       = aws_lambda_function.auto_tagger[0].arn
}

resource "aws_lambda_permission" "auto_tagger" {
  count = var.enable_auto_tagging ? 1 : 0

  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auto_tagger[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.auto_tagger[0].arn
}

# --- EC2 Scheduler Lambda ---
resource "aws_lambda_function" "scheduler" {
  count = var.enable_scheduler ? 1 : 0

  function_name = "${var.project_name}-scheduler"
  role          = var.lambda_role_arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60

  filename         = "${path.module}/../../lambda/scheduler.zip"
  source_code_hash = data.archive_file.scheduler[0].output_base64sha256

  environment {
    variables = {
      TAG_KEY    = "AutoScheduler"
      AWS_REGION = var.aws_region
    }
  }

  tags = var.common_tags
}

data "archive_file" "scheduler" {
  count       = var.enable_scheduler ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/scheduler"
  output_path = "${path.module}/../../lambda/scheduler.zip"
}

# --- Snapshot Cleanup Lambda ---
resource "aws_lambda_function" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  function_name = "${var.project_name}-snapshot-cleanup"
  role          = var.lambda_role_arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300

  filename         = "${path.module}/../../lambda/snapshot_cleanup.zip"
  source_code_hash = data.archive_file.snapshot_cleanup[0].output_base64sha256

  environment {
    variables = {
      RETENTION_DAYS = var.snapshot_retention_days
      DRY_RUN        = "true"
      AWS_REGION     = var.aws_region
    }
  }

  tags = var.common_tags
}

data "archive_file" "snapshot_cleanup" {
  count       = var.enable_snapshot_cleanup ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/snapshot_cleanup"
  output_path = "${path.module}/../../lambda/snapshot_cleanup.zip"
}

resource "aws_cloudwatch_event_rule" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  name                = "${var.project_name}-snapshot-cleanup-rule"
  description         = "Run snapshot cleanup Lambda function daily"
  schedule_expression = "cron(0 4 * * ? *)" # Daily at 4am UTC
}

resource "aws_cloudwatch_event_target" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  rule      = aws_cloudwatch_event_rule.snapshot_cleanup[0].name
  target_id = "SnapshotCleanupLambda"
  arn       = aws_lambda_function.snapshot_cleanup[0].arn
}

resource "aws_lambda_permission" "snapshot_cleanup" {
  count = var.enable_snapshot_cleanup ? 1 : 0

  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.snapshot_cleanup[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.snapshot_cleanup[0].arn
}
