resource "aws_kms_key" "shared_key" {
    description = "KMS key for S3 batch bucket"
    enable_key_rotation = true  
    policy = <<POLICY
{
 "Version": "2012-10-17",
 "Id": "key-default-1",
 "Statement": [
    {
    "Sid": "Allow administration of the key",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::${local.local_account_id}:root" },
    "Action": [
        "kms:Create*",
        "kms:Describe*",
        "kms:Enable*",
        "kms:List*",
        "kms:Put*",
        "kms:Update*",
        "kms:Revoke*",
        "kms:Disable*",
        "kms:Get*",
        "kms:Delete*",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion",
        "kms:GenerateDataKey*",
        "kms:Decrypt",
        "kms:Tag*"
        ],
        "Resource": "*"
    },
   {
     "Sid": "AllowAccountA",
     "Effect": "Allow",
     "Principal": {
       "AWS": "arn:aws:iam::${local.account_id}:root"
     },
     "Action": [
       "kms:Encrypt",
       "kms:Decrypt",
       "kms:GenerateDataKey*"
     ],
     "Resource": "*"
   }
 ]
}
POLICY
}

resource "aws_kms_alias" "shared_key" {
  name          = "alias/${local.prefix}-shared-key"
  target_key_id = aws_kms_key.shared_key.key_id
}

resource "aws_s3_bucket" "batch_data_source_bucket" {
    bucket        = "${local.prefix}-data-sources"
    force_destroy = local.is_temp
}

data "aws_iam_policy_document" "batch_data_source_bucket_policy" {
    source_policy_documents = [
        local.environment == "prod" ? templatefile("${local.policy_path}/s3_batch_policy_prod.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ):  templatefile("${local.policy_path}/s3_batch_policy.json", {
            "bucket-name" : aws_s3_bucket.batch_data_source_bucket.bucket
        } ),
        templatefile("${local.policy_path}/log_kinesis.json", {
            "kinesis_stream_name" : module.splunk.firehose_stream_name
        } ),
        
    ]
}

resource "aws_s3_bucket_policy" "batch_data_source_bucket_policy" {
   bucket = aws_s3_bucket.batch_data_source_bucket.id
   policy = data.aws_iam_policy_document.batch_data_source_bucket_policy.json
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_batch_encryption" {
  bucket = aws_s3_bucket.batch_data_source_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.shared_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket" "batch_data_destination_bucket" {
    bucket        = "${local.prefix}-data-destinations"
    force_destroy = local.is_temp
}