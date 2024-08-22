locals {
  forwarder_lambda_dir = abspath("${path.root}/../recordforwarder")
  forwarder_lambda_files         = fileset(local.forwarder_lambda_dir, "**")
  forwarding_lambda_dir_sha       = sha1(join("", [for f in local.forwarder_lambda_files : filesha1("${local.forwarder_lambda_dir}/${f}")]))
}

module "forwarding_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  create_ecr_repo = true
  ecr_repo        = "${local.prefix}-forwarding-repo"
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

# Policy for Lambda execution role to interact with logs, S3, and KMS.
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
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.prefix}-batch-data-destination",
          "arn:aws:s3:::${local.prefix}-batch-data-destination/*"       
        ]
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = "*"
      }
    ]
  })
}

locals {
  new_sqs_arn_map = { for key in tolist(var.suppliers) : key => data.aws_sqs_queue.processingqueues[key].arn }
}

# Policy for Lambda to interact with existing SQS FIFO Queues
resource "aws_iam_policy" "forwarding_lambda_sqs_policy" {
  name = "${local.prefix}-forwarding-lambda-sqs-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:SendMessage",
        "kms:Decrypt"
      ]
      Resource = [for queue in local.new_sqs_arn_map : queue]
    }]
  })
}

# Attach the execution policy to the Lambda role
resource "aws_iam_role_policy_attachment" "forwarding_lambda_exec_policy_attachment" {
  role       = aws_iam_role.forwarding_lambda_exec_role.name
  policy_arn = aws_iam_policy.forwarding_lambda_exec_policy.arn
}

# Attach the SQS policy to the Lambda role
resource "aws_iam_role_policy_attachment" "forwarding_lambda_sqs_policy_attachment" {
  role       = aws_iam_role.forwarding_lambda_exec_role.name
  policy_arn = aws_iam_policy.forwarding_lambda_sqs_policy.arn
}

# Permission for SQS to invoke Lambda function
resource "aws_lambda_permission" "allow_sqs_invoke_forwarder_lambda" {
  for_each      = local.new_sqs_arn_map
  statement_id  = "AllowSQSInvoke${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.forwarding_lambda.arn
  principal     = "sqs.amazonaws.com"
  source_arn    = each.value
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
      SOURCE_BUCKET_NAME = "${local.prefix}-batch-data-source"
      ACK_BUCKET_NAME    = "${local.prefix}-batch-data-destination"
      ENVIRONMENT        = local.environment
      LOCAL_ACCOUNT_ID   = local.local_account_id
      SHORT_QUEUE_PREFIX = local.short_queue_prefix
      PROD_ACCOUNT_ID    = local.account_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.forwarding_lambda_exec_policy_attachment,
    aws_iam_role_policy_attachment.forwarding_lambda_sqs_policy_attachment
  ]
}

resource "aws_lambda_event_source_mapping" "sqs_event_source_mapping_forwarder_lambda" {
  for_each         = local.new_sqs_arn_map
  event_source_arn = each.value
  function_name    = aws_lambda_function.forwarding_lambda.function_name
  batch_size       = 1
  enabled          = true

  depends_on = [aws_lambda_permission.allow_sqs_invoke_forwarder_lambda]
}
