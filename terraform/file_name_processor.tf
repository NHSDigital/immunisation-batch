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
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.prefix}-data-source",
          "arn:aws:s3:::${local.prefix}-data-source/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::${local.prefix}-data-destination",
          "arn:aws:s3:::${local.prefix}-data-destination/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = [
          "kms:Decrypt"
        ],
        Resource = "*"
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
          "arn:aws:s3:::${local.prefix}-config",
          "arn:aws:s3:::${local.prefix}-config/*"
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

# Lambda Function using Docker Image
resource "aws_lambda_function" "file_processor_lambda" {
  function_name   = "${local.prefix}-file_processor_lambda"
  role            = aws_iam_role.lambda_exec_role.arn
  package_type    = "Image"
  image_uri       = module.file_processor_docker_image.image_uri
  architectures   = ["x86_64"]
  timeout         = 60

  environment {
    variables = {
      SOURCE_BUCKET_NAME   = "${local.prefix}-data-source"
      ACK_BUCKET_NAME      = "${local.prefix}-data-destination"
      ENVIRONMENT          = local.environment
      LOCAL_ACCOUNT_ID     = local.local_account_id
      SHORT_QUEUE_PREFIX   = local.short_queue_prefix
      PROD_ACCOUNT_ID      = local.account_id
      CONFIG_BUCKET_NAME   = "${local.prefix}-config"
      REDIS_HOST           = aws_elasticache_cluster.redis_cluster.cache_nodes[0].address
      REDIS_PORT           = aws_elasticache_cluster.redis_cluster.port
    }
  }
  vpc_config {
    subnet_ids         = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]
    security_group_ids = [aws_security_group.lambda_security_group.id]
  }
}
resource "aws_security_group" "lambda_security_group" {
  name   = "${local.prefix}-lambda-security-group"
  vpc_id = data.aws_vpc.default.id
}

resource "aws_security_group" "redis_security_group" {
  name   = "${local.prefix}-redis-security-group"
  vpc_id = data.aws_vpc.default.id
}


# Ingress rule for Lambda security group allowing connections from Redis security group
resource "aws_security_group_rule" "lambda_ingress_from_redis" {
  type              = "ingress"
  from_port         = 6379
  to_port           = 6379
  protocol          = "tcp"
  security_group_id = aws_security_group.lambda_security_group.id
  source_security_group_id = aws_security_group.redis_security_group.id
}

# Egress rule for Lambda security group allowing all outbound traffic
resource "aws_security_group_rule" "lambda_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.lambda_security_group.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# Ingress rule for Redis security group allowing connections from Lambda security group
resource "aws_security_group_rule" "redis_ingress_from_lambda" {
  type              = "ingress"
  from_port         = 6379
  to_port           = 6379
  protocol          = "tcp"
  security_group_id = aws_security_group.redis_security_group.id
  source_security_group_id = aws_security_group.lambda_security_group.id
}

# Egress rule for Redis security group allowing all outbound traffic
resource "aws_security_group_rule" "redis_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.redis_security_group.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = "172.31.100.0/24"
  availability_zone = "eu-west-2a"
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id            = data.aws_vpc.default.id
  cidr_block        = "172.31.101.0/24"
  availability_zone = "eu-west-2b"
}



resource "aws_elasticache_cluster" "redis_cluster" {
  cluster_id           = "${local.prefix}-redis-cluster"
  engine               = "redis"
  node_type            = "cache.t2.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
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
  bucket = aws_s3_bucket.batch_config_bucket.bucket

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
  source_arn    = aws_s3_bucket.batch_config_bucket.arn
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
          "elasticache:CreateCacheCluster",
          "elasticache:DeleteCacheCluster",
          "elasticache:DescribeCacheClusters",
          "elasticache:ModifyCacheCluster",
          "elasticache:ListTagsForResource",
          "elasticache:AddTagsToResource",
          "elasticache:RemoveTagsFromResource"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach the policy to the ElastiCache role
resource "aws_iam_role_policy_attachment" "elasticache_policy_attachment" {
  role       = aws_iam_role.elasticache_exec_role.name
  policy_arn = aws_iam_policy.elasticache_permissions.arn
}