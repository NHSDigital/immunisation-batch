provider "aws" { 
  region = "eu-west-2"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy for Lambda execution role
resource "aws_iam_role_policy" "lambda_policy" {
  name   = "lambda-execution-policy"
  role   = aws_iam_role.lambda_role.id
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
        "sqs:SendMessage"
      ],
      Resource = "*"
    }]
  })
}

# Lambda Function
resource "aws_lambda_function" "file_processor_lambda" {
  function_name    = "file_processor_lambda"
  filename         = "file_processor_lambda.zip"
  source_code_hash = filebase64sha256("file_processor_lambda.zip")
  role             = aws_iam_role.lambda_role.arn
  handler          = "router_lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60

  environment {
    variables = {
      ACK_BUCKET_NAME = local.ack_bucket_name
      ENVIRONMENT     = local.environment
      ACCOUNT_ID      = lookup(local.account_ids, local.environment, var.internal_dev_account_id)
    }
  }
}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_lambda.function_name
  principal     = "s3.amazonaws.com"

  source_arn = "arn:aws:s3:::${var.environment == "internal-dev" ? "immunisation-batch-internal-dev-batch-data-source" : "immunisation-batch-${var.environment}-batch-data-source"}"
}

# S3 Bucket notification to trigger lambda function
resource "aws_s3_bucket_notification" "lambda_notification" {
  bucket = var.environment == "internal-dev" ? "immunisation-batch-internal-dev-batch-data-source" : "immunisation-batch-${var.environment}-batch-data-source"

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}
