# Archive the Lambda function code
data "archive_file" "file_transforming_lambda_zip" {  
  type        = "zip"  
  source_dir  = "${path.module}/../batch/src"
  output_path = "${path.module}/processing_lambda.zip"
}
# IAM Role for Lambda
resource "aws_iam_role" "processor_lambda_exec_role" {
  name = "${local.prefix}-processor-lambda-exec-role"
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
 
# Policy for Lambda execution role to interact with logs, S3, and KMS.
resource "aws_iam_policy" "processor_lambda_exec_policy" {
  name   = "${local.prefix}-processor-lambda-exec-policy"
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
        "s3:ListBucket",
        "kms:Decrypt",
      ],
      Resource = "*"
    }]
  })
}
locals {
  # Assuming var.suppliers is a list of supplier identifiers
  existing_sqs_arns_map = { for i, key in tolist(var.suppliers) : key => data.aws_sqs_queue.queues[key].arn }
} 
# Policy for Lambda to interact with existing SQS FIFO Queues
resource "aws_iam_policy" "processor_lambda_sqs_policy" {
  name = "${local.prefix}-processor-lambda-sqs-policy"
 
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:SendMessage",
        "kms: Decrypt"
      ],
      Resource = concat(
        [for queue in local.existing_sqs_arns_map : queue],
        [for queue in local.new_sqs_arns : queue]
      )
    }]
  })
}
 
# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "processor_lambda_exec_policy_attachment" {
  role       = aws_iam_role.processor_lambda_exec_role.name
  policy_arn = aws_iam_policy.processor_lambda_exec_policy.arn
}
 
# Attach the SQS policy to the Lambda role
resource "aws_iam_role_policy_attachment" "processor_lambda_sqs_policy_attachment" {
  role       = aws_iam_role.processor_lambda_exec_role.name
  policy_arn = aws_iam_policy.processor_lambda_sqs_policy.arn
}
 
# Permission for SQS to invoke Lambda function
resource "aws_lambda_permission" "allow_sqs_invoke" {
  for_each       = local.existing_sqs_arns_map
  statement_id   = "AllowSQSInvoke${each.key}"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.file_transforming_lambda.arn
  principal      = "sqs.amazonaws.com"
  source_arn     = each.value
}
 
# Lambda Function
resource "aws_lambda_function" "file_transforming_lambda" {
  function_name    = "${local.prefix}-file_transforming_lambda"
  filename         = data.archive_file.file_transforming_lambda_zip.output_path
  source_code_hash = data.archive_file.file_transforming_lambda_zip.output_base64sha256
  role             = aws_iam_role.processor_lambda_exec_role.arn
  handler          = "processing_lambda.process_lambda_handler"
  runtime          = "python3.8"
  timeout          = 60
 
  environment {
    variables = {
      SOURCE_BUCKET_NAME = "${local.prefix}-batch-data-source"
      ACK_BUCKET_NAME    = "${local.prefix}-batch-data-destination"
      ENVIRONMENT        = local.environment
      LOCAL_ACCOUNT_ID   = local.local_account_id
      SHORT_QUEUE_PREFIX = local.short_queue_prefix
      PROD_ACCOUNT_ID    = local.account_id
    }
    
  }  
}
resource "aws_lambda_event_source_mapping" "sqs_event_source_mapping" {
  for_each          = local.existing_sqs_arns_map
  event_source_arn  = each.value
  function_name     = aws_lambda_function.file_transforming_lambda.arn
  batch_size        = 1
  enabled           = true
}