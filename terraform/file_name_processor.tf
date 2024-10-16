# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  lambda_dir = abspath("${path.root}/../filenameprocessor")
  lambda_files         = fileset(local.lambda_dir, "**")
  lambda_dir_sha       = sha1(join("", [for f in local.lambda_files : filesha1("${local.lambda_dir}/${f}")]))
}

# Module for building and pushing Docker image to ECR
module "file_processor_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  create_ecr_repo = true
  ecr_repo        = "${local.prefix}-filename-processor-repo"
  ecr_repo_lifecycle_policy = jsonencode({
    "rules" : [
      {
        "rulePriority" : 1,
        "description" : "Keep only the last 2 images",
        "selection" : {
          "tagStatus" : "any",
          "countType" : "imageCountMoreThan",
          "countNumber" : 2
        },
        "action" : {
          "type" : "expire"
        }
      }
    ]
  })

  platform      = "linux/amd64"
  use_image_tag = false
  source_path   = local.lambda_dir
  triggers = {
    dir_sha = local.lambda_dir_sha
  }
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
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
       Resource = "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/lambda/${local.prefix}-file_processor_lambda:*"
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
        Effect   = "Allow",
        Action   = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
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
          "arn:aws:s3:::${data.aws_s3_bucket.existing_bucket.bucket}",           
          "arn:aws:s3:::${data.aws_s3_bucket.existing_bucket.bucket}/*"        
        ]
      }
    ]
  })
}

# Policy for Lambda to interact with SQS
resource "aws_iam_policy" "lambda_sqs_policy" {
  name = "${local.prefix}-lambda-sqs-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Action = [
        "sqs:SendMessage",
        "kms:Decrypt"
      ],
      Resource = [
        aws_sqs_queue.fifo_queue.arn
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

# Lambda Function with Security Group and VPC.
resource "aws_lambda_function" "file_processor_lambda" {
  function_name   = "${local.prefix}-file_name_processor_lambda"
  role            = aws_iam_role.lambda_exec_role.arn
  package_type    = "Image"
  image_uri       = module.file_processor_docker_image.image_uri
  architectures   = ["x86_64"]
  timeout         = 60

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [data.aws_security_group.existing_sg.id]
  }

  environment {
    variables = {
      SOURCE_BUCKET_NAME   = "${local.prefix}-data-sources"
      ACK_BUCKET_NAME      = "${local.prefix}-data-destinations"
      ENVIRONMENT          = local.environment
      LOCAL_ACCOUNT_ID     = local.local_account_id
      SHORT_QUEUE_PREFIX   = local.short_queue_prefix
      CONFIG_BUCKET_NAME   = data.aws_s3_bucket.existing_bucket.bucket
      REDIS_HOST           = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].address
      REDIS_PORT           = data.aws_elasticache_cluster.existing_redis.cache_nodes[0].port
    }
  }
}


# Permission for S3 to invoke Lambda function
resource "aws_lambda_permission" "s3_invoke_permission" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.batch_data_source_bucket.arn
}

# S3 Bucket notification to trigger Lambda function
resource "aws_s3_bucket_notification" "lambda_notification" {
  bucket = aws_s3_bucket.batch_data_source_bucket.bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}

# S3 Bucket notification to trigger Lambda function for config bucket
resource "aws_s3_bucket_notification" "new_lambda_notification" {
  bucket = data.aws_s3_bucket.existing_bucket.bucket

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }
}

# Permission for the new S3 bucket to invoke the Lambda function
resource "aws_lambda_permission" "new_s3_invoke_permission" {
  statement_id  = "AllowExecutionFromNewS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = data.aws_s3_bucket.existing_bucket.arn
}

# IAM Role for ElastiCache.
resource "aws_iam_role" "elasticache_exec_role" {
  name = "${local.prefix}-elasticache-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Sid = "",
      Principal = {
        Service = "elasticache.amazonaws.com" # ElastiCache service principal
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "elasticache_permissions" {
  name   = "${local.prefix}-elasticache-permissions"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheClusters",
          "elasticache:ListTagsForResource",
          "elasticache:AddTagsToResource",
          "elasticache:RemoveTagsFromResource"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.local_account_id}:cluster/immunisation-redis-cluster"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:CreateCacheCluster",
          "elasticache:DeleteCacheCluster",
          "elasticache:ModifyCacheCluster"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.local_account_id}:cluster/immunisation-redis-cluster"
        Condition = {
          "StringEquals": {
            "aws:RequestedRegion": "${var.aws_region}"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheSubnetGroups"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.local_account_id}:subnet-group/immunisation-redis-subnet-group"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:CreateCacheSubnetGroup",
          "elasticache:DeleteCacheSubnetGroup",
          "elasticache:ModifyCacheSubnetGroup"
        ]
        Resource = "arn:aws:elasticache:${var.aws_region}:${local.local_account_id}:subnet-group/immunisation-redis-subnet-group"
        Condition = {
          "StringEquals": {
            "aws:RequestedRegion": "${var.aws_region}"
          }
        }
      }
    ]
  })
}

# Attach the policy to the ElastiCache role
resource "aws_iam_role_policy_attachment" "elasticache_policy_attachment" {
  role       = aws_iam_role.elasticache_exec_role.name
  policy_arn = aws_iam_policy.elasticache_permissions.arn
}