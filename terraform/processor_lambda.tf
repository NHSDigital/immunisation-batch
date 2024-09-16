# Define the ECS Cluster
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "${local.prefix}-ecs-cluster"
}

# Locals for Lambda processing paths and hash
locals {
  processing_lambda_dir     = abspath("${path.root}/../recordprocessor")
  processing_lambda_files   = fileset(local.processing_lambda_dir, "**")
  processing_lambda_dir_sha = sha1(join("", [for f in local.processing_lambda_files : filesha1("${local.processing_lambda_dir}/${f}")]))
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

# Define the IAM Role for ECS Task Execution with Kinesis Permissions
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
        Resource = local.new_kinesis_arns
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
        value = jsonencode(local.new_kinesis_arns)
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

# Define the ECS Service to Run the Task Definition
resource "aws_ecs_service" "ecs_service" {
  name            = "${local.prefix}-processor-service"
  cluster         = aws_ecs_cluster.ecs_cluster.id
  task_definition = aws_ecs_task_definition.ecs_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
            subnets          = data.aws_subnets.default.ids
            assign_public_ip = true
        }
}

#  Retrieve SQS Queues 
data "aws_sqs_queue" "queues" {
  for_each = toset(var.suppliers)
  name     = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-metadata-queue.fifo"
  
  # Ensure the queue exists before looking it up
  depends_on = [aws_sqs_queue.fifo_queues]
}

# Create IAM Role for EventBridge to Trigger ECS Task
resource "aws_iam_role" "eventbridge_ecs_role" {
  name = "${local.prefix}-eventbridge-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "events.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# Attach the ECS Task Execution Role to EventBridge role
resource "aws_iam_role_policy_attachment" "eventbridge_ecs_role_policy_attachment" {
  role       = aws_iam_role.eventbridge_ecs_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for ECS task execution triggered by EventBridge
resource "aws_iam_policy" "eventbridge_ecs_policy" {
  name   = "${local.prefix}-eventbridge-ecs-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ecs:RunTask",
          "ecs:StartTask"
        ],
        Resource = aws_ecs_task_definition.ecs_task.arn
      },
      {
        Effect   = "Allow",
        Action   = [
          "iam:PassRole"
        ],
        Resource = aws_iam_role.ecs_task_exec_role.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eventbridge_ecs_policy_attachment" {
  role       = aws_iam_role.eventbridge_ecs_role.name
  policy_arn = aws_iam_policy.eventbridge_ecs_policy.arn
}

# Create CloudWatch Event Rule for SQS Queues to Trigger ECS Task
resource "aws_cloudwatch_event_rule" "ecs_trigger_rule" {
  name        = "${local.prefix}-ecs-trigger-rule"
  description = "Trigger ECS task when a message arrives in any SQS queue"

  event_pattern = jsonencode({
    "source": ["aws.sqs"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["sqs.amazonaws.com"],
      "eventName": ["SendMessage"],
      "requestParameters": {
        "queueUrl": local.existing_sqs_arns
      }
    }
  })
}

#  Create CloudWatch Event Target to Trigger ECS Task
resource "aws_cloudwatch_event_target" "ecs_trigger_target" {
  rule      = aws_cloudwatch_event_rule.ecs_trigger_rule.name
  arn       = aws_ecs_cluster.ecs_cluster.arn
  role_arn  = aws_iam_role.eventbridge_ecs_role.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.ecs_task.arn
    launch_type         = "FARGATE"
    network_configuration {
            subnets          = data.aws_subnets.default.ids
            assign_public_ip = true
        }
    platform_version = "LATEST"
  }
}

#  Define Variables for Subnets, VPC ID, and AWS Region
data "aws_vpc" "default" {
    default = true
}
data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}


variable "aws_region" {
  description = "AWS Region"
  default     = "eu-west-2"
}