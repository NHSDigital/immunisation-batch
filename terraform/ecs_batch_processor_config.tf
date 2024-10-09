# Define the ECS Cluster
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "${local.prefix}-ecs-cluster"
}

# Locals for Lambda processing paths and hash
locals {
  processing_lambda_dir     = abspath("${path.root}/../recordprocessor")
  path_include              = ["**"]
  path_exclude              = ["**/__pycache__/**"]
  files_include             = setunion([for f in local.path_include : fileset(local.processing_lambda_dir, f)]...)
  files_exclude             = setunion([for f in local.path_exclude : fileset(local.processing_lambda_dir, f)]...)
  processing_lambda_files   = sort(setsubtract(local.files_include, local.files_exclude))
  processing_lambda_dir_sha = sha1(join("", [for f in local.processing_lambda_files : filesha1("${local.processing_lambda_dir}/${f}")]))
  image_tag = "latest"
}

# Create ECR Repository for processing.
resource "aws_ecr_repository" "processing_repository" {
  name = "${local.prefix}-processing-repo"
}

# Build and Push Docker Image to ECR (Reusing the existing module)
module "processing_docker_image" {
  source = "terraform-aws-modules/lambda/aws//modules/docker-build"

  docker_file_path           = "Dockerfile"
  create_ecr_repo            = false
  ecr_repo                   = aws_ecr_repository.processing_repository.name
  ecr_repo_lifecycle_policy   = jsonencode({
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

resource "aws_iam_role_policy_attachment" "task_execution_ecr_policy" {
    role       = aws_iam_role.ecs_task_exec_role.name
    policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
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
          "arn:aws:s3:::${local.prefix}-data-sources",
          "arn:aws:s3:::${local.prefix}-data-sources/*",
          "arn:aws:s3:::${local.prefix}-data-destinations",
          "arn:aws:s3:::${local.prefix}-data-destinations/*",
          "arn:aws:s3:::${local.prefix}-configs",
          "arn:aws:s3:::${local.prefix}-configs/*"
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
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "ecr:GetAuthorizationToken"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_exec_policy_attachment" {
  role       = aws_iam_role.ecs_task_exec_role.name
  policy_arn = aws_iam_policy.ecs_task_exec_policy.arn
}

resource "aws_cloudwatch_log_group" "ecs_task_log_group" {
  name              = "/aws/vendedlogs/ecs/${local.prefix}-processor-task"
}

# Create the ECS Task Definition
# Update ECS Task Definition with VPC Subnet IDs and Security Group
resource "aws_ecs_task_definition" "ecs_task" {
  family                   = "${local.prefix}-processor-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  task_role_arn            = aws_iam_role.ecs_task_exec_role.arn
  execution_role_arn       = aws_iam_role.ecs_task_exec_role.arn

  container_definitions = jsonencode([{
    name      = "${local.prefix}-processor-container"
    image     = "${aws_ecr_repository.processing_repository.repository_url}:${local.image_tag}"
    essential = true
    environment = [
      {
        name  = "SOURCE_BUCKET_NAME"
        value = "${local.prefix}-data-sources"
      },
      {
        name  = "ACK_BUCKET_NAME"
        value = "${local.prefix}-data-destinations"
      },
      {
        name  = "ENVIRONMENT"
        value = "${local.environment}"
      },
      {
        name  = "SHORT_QUEUE_PREFIX"
        value = "${local.short_queue_prefix}"
      },
      {
        name  = "CONFIG_BUCKET_NAME"
        value = "${local.prefix}-configs"
      },
      {
        name  = "KINESIS_STREAM_ARN"
        value = "${local.new_kinesis_arn}"
      },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/aws/vendedlogs/ecs/${local.prefix}-processor-task"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
  depends_on = [aws_cloudwatch_log_group.ecs_task_log_group]
}


# IAM Role for EventBridge Pipe
resource "aws_iam_role" "fifo_pipe_role" {
name = "${local.prefix}-eventbridge-pipe-role"
assume_role_policy = jsonencode({
   Version = "2012-10-17"
   Statement = [
     {
       Action = "sts:AssumeRole"
       Effect = "Allow"
       Principal = {
         Service = "pipes.amazonaws.com"
       }
     }
   ]
})
}
resource "aws_iam_policy" "fifo_pipe_policy" {
   name   = "${local.prefix}-fifo-pipe-policy"
   policy = jsonencode({
     Version = "2012-10-17"
     Statement = [
       {
         Action = [
           "sqs:ReceiveMessage",
           "sqs:DeleteMessage",
           "sqs:GetQueueAttributes",
           "ecs:RunTask",
           "ecs:StartTask",
           "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents"
         ]
         Effect = "Allow"
         Resource = "*"
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

 resource "aws_iam_role_policy_attachment" "fifo_pipe_policy_attachment" {
   role       = aws_iam_role.fifo_pipe_role.name
   policy_arn = aws_iam_policy.fifo_pipe_policy.arn
 }

 
# EventBridge Pipe
resource "aws_pipes_pipe" "fifo_pipe" {
  name       = "${local.prefix}-pipe"
  role_arn   = aws_iam_role.fifo_pipe_role.arn
  source     = "arn:aws:sqs:eu-west-2:${local.local_account_id}:${local.short_prefix}-metadata-queue.fifo"
  target     = aws_ecs_cluster.ecs_cluster.arn
  
  target_parameters {
    ecs_task_parameters {
      task_definition_arn = aws_ecs_task_definition.ecs_task.arn
      launch_type         = "FARGATE"
      network_configuration {
        aws_vpc_configuration {
          subnets         = data.aws_subnets.default.ids
          security_groups = [aws_security_group.lambda_sg.id]
          assign_public_ip = "ENABLED"          
        }
      }
      overrides {
        container_override {
          cpu = 256
          name = "${local.prefix}-processor-container"
          environment {
            name  = "EVENT_DETAILS"
            value = "$.body"
          }
          memory = 512
          memory_reservation = 512
        }
      }
      task_count = 1
    }
    
 }
 log_configuration {
    include_execution_data = ["ALL"]
    level                  = "ERROR"
    cloudwatch_logs_log_destination {
      log_group_arn = aws_cloudwatch_log_group.pipe_log_group.arn
    }
  }
}

# Custom Log Group
resource "aws_cloudwatch_log_group" "pipe_log_group" {
  name = "/aws/vendedlogs/pipes/${local.prefix}-pipe-logs"
}
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type = "Interface"
  subnet_ids        = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_sg.id]
  tags = {
    Name = "${var.project_name}-${local.environment}-ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type = "Interface"
  subnet_ids        = data.aws_subnets.default.ids
  security_group_ids = [aws_security_group.lambda_sg.id]
  tags = {
    Name = "${var.project_name}-${local.environment}-ecr-dkr-endpoint"
  }
}

# aws_ecr_repository_policy
resource "aws_ecr_repository_policy" "processing_repository_policy" {
  repository = aws_ecr_repository.processing_repository.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = "*",
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ],
        Resource = aws_ecr_repository.processing_repository.arn
      }
    ]
  })
}

