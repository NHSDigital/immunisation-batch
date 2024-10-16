resource "aws_s3_bucket" "batch_config_bucket" {
    bucket        = "imms-internal-dev-supplier-config"
}

resource "aws_s3_bucket_public_access_block" "batch_config_bucket-public-access-block" {
  bucket = aws_s3_bucket.batch_config_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}