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
  image_scanning_configuration {
    scan_on_push = true
  }
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
        Resource = "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/vendedlogs/ecs/${local.prefix}-processor-task:*"
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
        Resource = [ data.aws_kms_key.existing_s3_encryption_key.arn,
                     data.aws_kms_key.existing_kinesis_encryption_key.arn
             ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = [ data.aws_kms_key.existing_s3_encryption_key.arn,
                     data.aws_kms_key.existing_kinesis_encryption_key.arn
        ]
      },
      {
        Effect   = "Allow",
        Action   = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ],
        Resource = "arn:aws:kinesis:${var.aws_region}:${local.local_account_id}:stream/${local.short_prefix}-processingdata-stream"
      },
      {
        Effect   = "Allow",
        Action   = [
          "ecr:GetAuthorizationToken"
        ],
        Resource = "arn:aws:ecr:${var.aws_region}:${local.local_account_id}:repository/${local.short_prefix}-processing-repo"
      },
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = data.aws_lambda_function.existing_search_lambda.arn       
      },
      {
        Effect= "Allow",
        Action= [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "kms:Decrypt"
        ],
        Resource= ["arn:aws:sqs:${var.aws_region}:${local.local_account_id}:imms-${local.api_env}-ack-metadata-queue.fifo"]
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
resource "aws_ecs_task_definition" "ecs_task" {
  family                   = "${local.prefix}-processor-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "8192"
  runtime_platform {
        operating_system_family = "LINUX"
        cpu_architecture        = "X86_64"
    }
  task_role_arn            = aws_iam_role.ecs_task_exec_role.arn
  execution_role_arn       = aws_iam_role.ecs_task_exec_role.arn

  container_definitions = jsonencode([{
    name      = "${local.prefix}-process-records-container"
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
      { name  = "SPLUNK_FIREHOSE_NAME"
        value = data.aws_kinesis_firehose_delivery_stream.splunk_stream.name},
      {
        name  = "SEARCH_IMMS_LAMBDA"
        value = data.aws_lambda_function.existing_search_lambda.function_name
      },
      {
        name="LOCAL_ACCOUNT_ID"   
        value ="${tostring(local.local_account_id)}"
      }

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
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "pipes:CreatePipe",
          "pipes:StartPipe",
          "pipes:StopPipe",
          "pipes:DeletePipe",
          "pipes:UpdatePipe",
          "pipes:DescribePipe"
        ],
        Resource = [
          "arn:aws:pipes:${var.aws_region}:${local.local_account_id}:pipe/${local.prefix}-pipe",
          aws_ecs_task_definition.ecs_task.arn
        ]
      },
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
        ],
        Effect = "Allow",
        Resource = [
          "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/vendedlogs/pipes/${local.prefix}-pipe-logs:*",
          "arn:aws:ecs:${var.aws_region}:${local.local_account_id}:task/${local.prefix}-ecs-cluster/*",
          "arn:aws:logs:${var.aws_region}:${local.local_account_id}:log-group:/aws/vendedlogs/ecs/${local.prefix}-processor-task:*",
          "arn:aws:sqs:${var.aws_region}:${local.local_account_id}:${local.short_prefix}-metadata-queue.fifo",
          "arn:aws:ecs:${var.aws_region}:${local.local_account_id}:cluster/${local.prefix}-ecs-cluster",
          aws_ecs_task_definition.ecs_task.arn
        ]
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
          assign_public_ip = "ENABLED"
        }
      }
      overrides {
        container_override {
          cpu = 1024
          name = "${local.prefix}-process-records-container"
          environment {
            name  = "EVENT_DETAILS"
            value = "$.body"
          }
          memory = 3072
          memory_reservation = 1024
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
