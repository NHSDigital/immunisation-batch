locals {
  forwarder_lambda_dir      = abspath("${path.root}/../recordforwarder")
  forwarder_lambda_files    = fileset(local.forwarder_lambda_dir, "**")
  forwarding_lambda_dir_sha = sha1(join("", [for f in local.forwarder_lambda_files : filesha1("${local.forwarder_lambda_dir}/${f}")]))
}

resource "aws_ecr_repository" "forwarder_lambda_repository" {
  image_scanning_configuration {
    scan_on_push = true
  }
  name = "${local.prefix}-forwarding-repo"
}

module "forwarding_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  create_ecr_repo          = false
  ecr_repo                 = aws_ecr_repository.forwarder_lambda_repository.name
  ecr_repo_lifecycle_policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 2 images"
        selection = {
          tagStatus  = "any"
          countType  = "imageCountMoreThan"
          countNumber = 2
        }
        action = {
          type = "expire"
        }
      }
    ]
  })

  platform      = "linux/amd64"
  use_image_tag = false
  source_path   = local.forwarder_lambda_dir
  triggers = {
    dir_sha = local.forwarding_lambda_dir_sha
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "forwarding_lambda_exec_role" {
  name = "${local.prefix}-forwarding-lambda-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow"
      Sid    = ""
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Policy for Lambda execution role to interact with logs, S3, KMS, and Kinesis.
resource "aws_iam_policy" "forwarding_lambda_exec_policy" {
  name   = "${local.prefix}-forwarding-lambda-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/lambda/${local.prefix}-forwarding_lambda:*",
      },
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.prefix}-data-sources",           
          "arn:aws:s3:::${local.prefix}-data-sources/*"        
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.prefix}-data-destinations",       
          "arn:aws:s3:::${local.prefix}-data-destinations/*"        
        ]
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "arn:aws:kms:${var.aws_region}:${local.local_account_id}:key/*"
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
         Resource = ["arn:aws:secretsmanager:${var.aws_region}:${local.local_account_id}:secret:imms/immunization/int/*",
        "arn:aws:secretsmanager:${var.aws_region}:${local.local_account_id}:secret:imms/immunization/internal-dev/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:DescribeStream",
          "kinesis:ListStreams"
        ]
       Resource = "arn:aws:kinesis:${var.aws_region}:${local.local_account_id}:stream/${local.short_prefix}-processingdata-stream"
      },
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = [
          data.aws_lambda_function.existing_create_lambda.arn,           
          data.aws_lambda_function.existing_update_lambda.arn,
          data.aws_lambda_function.existing_delete_lambda.arn        
        ]
      }
    ]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "forwarding_lambda_exec_policy_attachment" {
  role       = aws_iam_role.forwarding_lambda_exec_role.name
  policy_arn = aws_iam_policy.forwarding_lambda_exec_policy.arn
}

# Lambda Function
resource "aws_lambda_function" "forwarding_lambda" {
  function_name  = "${local.prefix}-forwarding_lambda"
  role           = aws_iam_role.forwarding_lambda_exec_role.arn
  package_type   = "Image"
  architectures  = ["x86_64"]
  image_uri      = module.forwarding_docker_image.image_uri
  timeout        = 60

  environment {
    variables = {
      SOURCE_BUCKET_NAME = "${local.prefix}-data-sources"
      ACK_BUCKET_NAME    = "${local.prefix}-data-destinations"
      ENVIRONMENT        = local.environment
      LOCAL_ACCOUNT_ID   = local.local_account_id
      SHORT_QUEUE_PREFIX = local.short_queue_prefix
      CREATE_LAMBDA_NAME = data.aws_lambda_function.existing_create_lambda.function_name
      UPDATE_LAMBDA_NAME = data.aws_lambda_function.existing_update_lambda.function_name
      DELETE_LAMBDA_NAME = data.aws_lambda_function.existing_delete_lambda.function_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.forwarding_lambda_exec_policy_attachment
  ]
}

 resource "aws_lambda_event_source_mapping" "kinesis_event_source_mapping_forwarder_lambda" {
    event_source_arn  = local.new_kinesis_arn
    function_name     = aws_lambda_function.forwarding_lambda.function_name
    starting_position = "LATEST"
    batch_size        = 1
    enabled           = true

   depends_on = [aws_lambda_function.forwarding_lambda]
 }
 