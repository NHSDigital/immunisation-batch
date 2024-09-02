resource "aws_s3_bucket" "batch_config_bucket" {
    bucket        = "${local.prefix}-config"
    force_destroy = local.is_temp
}

