resource "aws_s3_bucket" "batch_config_bucket" {
    bucket        = "${local.prefix}-batch-config"
    force_destroy = local.is_temp
}

