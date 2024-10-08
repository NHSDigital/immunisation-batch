resource "aws_s3_bucket" "batch_config_bucket" {
  bucket        = "${local.prefix}-configs"
  force_destroy = local.is_temp
}

resource "aws_s3_bucket_policy" "batch_config_bucket_policy" {
  bucket = aws_s3_bucket.batch_config_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          AWS = aws_iam_role.lambda_exec_role.arn
        },
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::${local.prefix}-configs",
          "arn:aws:s3:::${local.prefix}-configs/*"
        ],
        Condition = {
          StringEquals = {
            "aws:SourceVpce" = "vpce-0de54bdb3ae4df740"
          }
        }
      }
    ]
  })
}