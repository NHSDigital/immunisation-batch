resource "aws_security_group" "lambda_redis_sg" {
  vpc_id = data.aws_vpc.default.id
  name   = "immunisation-security-group"
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_vpc_endpoint" "sqs_endpoint" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type = "Interface"

  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.lambda_redis_sg.id]
  private_dns_enabled = true

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "kms:Decrypt"
        ]
        Resource  = "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-sqs-endpoint"
  }
}

resource "aws_vpc_endpoint" "s3_endpoint" {
  vpc_id       = data.aws_vpc.default.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  route_table_ids = [
    for rt in data.aws_route_tables.default_route_tables.ids : rt
  ]

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*",
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource  = "*"
      }
    ]
  })
  tags = {
    Name = "immunisation-s3-endpoint"
  }
}