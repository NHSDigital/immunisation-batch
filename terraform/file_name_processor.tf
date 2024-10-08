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
          "arn:aws:s3:::${local.prefix}-configs",           
          "arn:aws:s3:::${local.prefix}-configs/*"        
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
  function_name   = "${local.prefix}-file_processor_lambda"
  role            = aws_iam_role.lambda_exec_role.arn
  package_type    = "Image"
  image_uri       = module.file_processor_docker_image.image_uri
  architectures   = ["x86_64"]
  timeout         = 60

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      SOURCE_BUCKET_NAME   = "${local.prefix}-data-sources"
      ACK_BUCKET_NAME      = "${local.prefix}-data-destinations"
      ENVIRONMENT          = local.environment
      LOCAL_ACCOUNT_ID     = local.local_account_id
      SHORT_QUEUE_PREFIX   = local.short_queue_prefix
      PROD_ACCOUNT_ID      = local.account_id
      CONFIG_BUCKET_NAME   = "${local.prefix}-configs"
      REDIS_HOST           = aws_elasticache_cluster.redis_cluster.cache_nodes[0].address
      REDIS_PORT           = aws_elasticache_cluster.redis_cluster.port
    }
  }
}

# ElastiCache Cluster for Redis with Security Group
resource "aws_elasticache_cluster" "redis_cluster" {
  cluster_id           = "${local.prefix}-redis-cluster"
  engine               = "redis"
  node_type            = "cache.t2.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  security_group_ids   = [aws_security_group.redis_sg.id]
  subnet_group_name    = aws_elasticache_subnet_group.redis_subnet_group.name
}

# Subnet Group for Redis
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name       = "${local.prefix}-redis-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
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
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:CreateCacheSubnetGroup",
          "elasticache:DeleteCacheSubnetGroup",
          "elasticache:DescribeCacheSubnetGroups",
          "elasticache:ModifyCacheSubnetGroup"
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
# Create Lambda Security Group without rules
resource "aws_security_group" "lambda_sg" {
  name   = "${local.prefix}-lambda-sg"
  vpc_id = data.aws_vpc.default.id
}

# Create Redis Security Group without rules
resource "aws_security_group" "redis_sg" {
  name   = "${local.prefix}-redis-sg"
  vpc_id = data.aws_vpc.default.id
}

# Add egress rule to Lambda SG to allow outbound traffic to Redis on port 6379
resource "aws_security_group_rule" "lambda_to_redis" {
  type              = "egress"
  from_port         = 6379
  to_port           = 6379
  protocol          = "tcp"
  security_group_id = aws_security_group.lambda_sg.id
  source_security_group_id = aws_security_group.redis_sg.id
}

# Add ingress rule to Redis SG to allow inbound traffic from Lambda SG on port 6379
resource "aws_security_group_rule" "redis_from_lambda" {
  type              = "ingress"
  from_port         = 6379
  to_port           = 6379
  protocol          = "tcp"
  security_group_id = aws_security_group.redis_sg.id
  source_security_group_id = aws_security_group.lambda_sg.id
}

# Egress rule to allow all outbound traffic from Lambda to internet
resource "aws_security_group_rule" "lambda_sg_internet_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.lambda_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# Ingress rule to allow inbound connections to Redis (if needed for management)
resource "aws_security_group_rule" "redis_sg_inbound_management" {
  type              = "ingress"
  from_port         = 6379
  to_port           = 6379
  protocol          = "tcp"
  security_group_id = aws_security_group.redis_sg.id
  cidr_blocks       = ["0.0.0.0/0"] # Replace with your trusted CIDR range if needed
}
# Allow Lambda to communicate with SQS over HTTPS (port 443)
resource "aws_security_group_rule" "lambda_to_sqs_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.lambda_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# VPC Endpoint for S3
resource "aws_vpc_endpoint" "s3_endpoint" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  route_table_ids = [
    for rt in data.aws_route_tables.default_route_tables.ids : rt
  ]

  # Control access to the VPC endpoint
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow"
      Principal = {
      AWS = "arn:aws:iam::${local.local_account_id}:root"
    }
      Action    = "s3:*"
      Resource  = [
      # Bucket 1
      "arn:aws:s3:::${local.prefix}-configs",
      "arn:aws:s3:::${local.prefix}-configs/*",
      "arn:aws:s3:::${local.prefix}--data-sources", 
      "arn:aws:s3:::${local.prefix}--data-sources/*",
      "arn:aws:s3:::${local.prefix}--data-destinations",
      "arn:aws:s3:::${local.prefix}--data-destinations/*"
    ]
    }]
  })
   tags = {
    Name = "${var.project_name}-${local.environment}-s3-endpoint"
  }
}

# Get the Route Tables for the default VPC
data "aws_route_tables" "default_route_tables" {
  vpc_id = data.aws_vpc.default.id
}
# VPC Endpoint for SQS
resource "aws_vpc_endpoint" "sqs_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.eu-west-2.sqs"
  vpc_endpoint_type = "Interface"

  subnet_ids = data.aws_subnets.default.ids

  security_group_ids = [
    aws_security_group.lambda_sg.id
  ]

  private_dns_enabled = true

  # Policy to control access to the SQS endpoint
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = {
      AWS = "arn:aws:iam::${local.local_account_id}:root"
    }
      Action    = "sqs:*",
      Resource  = [
        "arn:aws:sqs:eu-west-2:${local.local_account_id}:${local.short_prefix}-${local.environment}-metadata-queue.fifo",
      ]
    }]
  })
  tags = {
    Name = "${var.project_name}-${local.environment}-sqs-endpoint"
  }
}
resource "aws_security_group_rule" "vpc_endpoint_sqs_ingress" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.lambda_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}
