# Archive the Lambda function code
data "archive_file" "file_transforming_lambda_zip" {  
  type        = "zip"  
  source_dir  = "${path.module}/../batch/src" 
  output_path = "${path.module}/processing_lambda.zip"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "${local.prefix}-lambda-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid = "",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy for Lambda execution role to interact with logs, S3, and KMS
resource "aws_iam_policy" "lambda_exec_policy" {
  name   = "${local.prefix}-lambda-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "s3:GetObject",
        "s3:PutObject",
        "kms:Decrypt"
      ],
      Resource = "*"
    }]
  })
}

# Policy for Lambda to interact with existing SQS FIFO Queues
resource "aws_iam_policy" "lambda_sqs_policy" {
  name = "${local.prefix}-lambda-sqs-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      Resource = [
        for queue in var.existing_sqs_arns : queue
      ]
    }]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_exec_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_exec_policy.arn
}

# Attach the SQS policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_sqs_policy_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_sqs_policy.arn
}

# Lambda Function
resource "aws_lambda_function" "file_transforming_lambda" {
  function_name    = "${local.prefix}-file_transforming_lambda"
  filename         = data.archive_file.file_transforming_lambda_zip.output_path
  source_code_hash = data.archive_file.file_transforming_lambda_zip.output_base64sha256
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "processing_lambda.process_lambda_handler"
  runtime          = "python3.8"
  timeout          = 60

  environment {
    variables = {
      ACK_BUCKET_NAME    = "${local.prefix}-batch-data-destination"
      ENVIRONMENT        = local.environment
      LOCAL_ACCOUNT_ID   = local.local_account_id
      SHORT_QUEUE_PREFIX = local.short_queue_prefix
      PROD_ACCOUNT_ID    = local.account_id
    }
  }

  # Adding SQS trigger for each existing queue
  dynamic "event_source_mapping" {
    for_each = var.existing_sqs_arns
    content {
      event_source_arn = event_source_mapping.value
      batch_size       = 1
      enabled          = true
    }
  }
}