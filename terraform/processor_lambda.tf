# Define the ECS Cluster
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "${local.prefix}-ecs-cluster"
}

# Build and Push Docker Image to ECR (Reusing the existing module)
module "processing_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  create_ecr_repo = true
  ecr_repo        = "${local.prefix}-processing-repo"
  platform      = "linux/amd64"
  use_image_tag = false
  source_path   = local.processing_lambda_dir
  triggers = {
    dir_sha = local.processing_lambda_dir_sha
  }
}

# Define the IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_exec_role" {
  name = "${local.prefix}-ecs-task-exec-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach the necessary policies for ECS task execution (logs, ECR pull, S3, KMS, Secrets Manager, Kinesis)
resource "aws_iam_policy" "ecs_task_exec_policy" {
  name   = "${local.prefix}-ecs-task-exec-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject"
        ],
        Resource = [
          "arn:aws:s3:::${local.prefix}-data-source",
          "arn:aws:s3:::${local.prefix}-data-source/*",
          "arn:aws:s3:::${local.prefix}-data-destination",
          "arn:aws:s3:::${local.prefix}-data-destination/*",
          "arn:aws:s3:::${local.prefix}-config",
          "arn:aws:s3:::${local.prefix}-config/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = "kms:Decrypt",
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = "secretsmanager:GetSecretValue",
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ],
        Resource = local.new_stream_arns
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_exec_policy_attachment" {
  role       = aws_iam_role.ecs_task_exec_role.name
  policy_arn = aws_iam_policy.ecs_task_exec_policy.arn
}

# Create the ECS Task Definition
resource "aws_ecs_task_definition" "ecs_task" {
  family                   = "${local.prefix}-processor-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_exec_role.arn

  container_definitions = jsonencode([{
    name      = "processor-container"
    image     = module.processing_docker_image.image_uri
    essential = true
    environment = [
      {
        name  = "SOURCE_BUCKET_NAME"
        value = "${local.prefix}-data-source"
      },
      {
        name  = "ACK_BUCKET_NAME"
        value = "${local.prefix}-data-destination"
      },
      {
        name  = "ENVIRONMENT"
        value = local.environment
      },
      {
        name  = "CONFIG_BUCKET_NAME"
        value = "${local.prefix}-config"
      },
      {
        name  = "KINESIS_STREAM_ARN"
        value = jsonencode(local.new_stream_arns)
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${local.prefix}-processor-task"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

# Create Security Group for ECS Tasks
resource "aws_security_group" "ecs_security_group" {
  name        = "${local.prefix}-ecs-sg"
  description = "Security group for ECS processor tasks"
  vpc_id      = var.vpc_id != "" ? var.vpc_id : data.aws_vpc.default.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Define the ECS Service to Run the Task Definition
resource "aws_ecs_service" "ecs_service" {
  name            = "${local.prefix}-processor-service"
  cluster         = aws_ecs_cluster.ecs_cluster.id
  task_definition = aws_ecs_task_definition.ecs_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = length(var.subnets) > 0 ? var.subnets : data.aws_subnet_ids.default.ids
    assign_public_ip = true
    security_groups = [aws_security_group.ecs_security_group.id]
  }
}

# Data lookup for created streams, ensuring the streams exist before lookup
data "aws_kinesis_stream" "processingstreams" {
  for_each = toset(var.suppliers)
  name     = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-processingdata-stream"

  depends_on = [aws_kinesis_stream.processor_streams]
}

locals {
  # Creating a list of Kinesis Stream ARNs for use elsewhere
  new_stream_arns = [for stream in data.aws_kinesis_stream.processingstreams : stream.arn]
}

data "aws_subnet_ids" "default" {
  vpc_id = data.aws_vpc.default.id
}

#  Define Variables for Subnets, VPC ID, and AWS Region
variable "subnets" {
  description = "List of subnets for ECS tasks"
  type        = list(string)
  default     = []
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS Region"
  default     = "eu-west-2"
}
