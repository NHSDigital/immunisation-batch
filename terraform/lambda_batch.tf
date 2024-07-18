# zip python lambda file_processor_lambda
data "archive_file" "lambda_zip" {  
  type = "zip"  
  source_dir = "${path.module}/../batch/src" 
  output_path = "${path.module}/router_lambda_function.zip"
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

# Policy for Lambda execution role
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
        "sqs:SendMessage"
      ],
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment""lambda_exec_policy_attachment" {
  role = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_exec_policy.arn
}

# Lambda Function
resource "aws_lambda_function" "file_processor_lambda" {
  function_name    = "${local.prefix}-file_processor_lambda"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "router_lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60

  environment {
    variables = {
      ACK_BUCKET_NAME = "${local.prefix}-batch-data-destination"
      ENVIRONMENT     = local.environment
      ACCOUNT_ID      = local.account_id
    }
  }
}

# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_lambda.function_name
  principal     = "s3.amazonaws.com"

  source_arn = aws_s3_bucket.batch_data_source_bucket.arn
}

# S3 Bucket notification to trigger lambda function
resource "aws_s3_bucket_notification" "lambda_notification" {
  bucket = aws_s3_bucket.batch_data_source_bucket.bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}
