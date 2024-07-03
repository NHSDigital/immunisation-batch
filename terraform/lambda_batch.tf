provider "aws" { 
  region = "eu-west-2"
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}


//Policy for Lambda execution role
resource

//defined lambda function
resource "aws_lambda_function" "file_processor_lambda" {
  function_name    = "file_processor_lambda"
  filename         = "file_processor_lambda.zip"
  source_code_hash = filebase64sha256("router_lambda_function.py.zip")
  role             = aws_iam_role.lambda_role.arn
  handler          = "router_lambda_function.lambda_handler"
  runtime          = "python3.8"
  timeout          = 60

  environment {
    variables = {
      ACK_BUCKET_NAME = "immunisation-fhir-api-int-batch-data-destination"
    }
  }
}

// permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_lambda.function_name
  principal     = "s3.amazonaws.com"

  source_arn = aws_s3_bucket.immunisation_fhir_api_int_batch_data_source.arn
}


//S3 Bucket notification to trigger lambda function
resource "aws_s3_bucket_notification" "lambda_notification" {
  bucket = aws_s3_bucket.immunisation_fhir_api_int_batch_data_source.bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}
