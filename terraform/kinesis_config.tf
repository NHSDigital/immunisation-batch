# Define the Kinesis Data Stream resource with 15 shards
resource "aws_kinesis_stream" "processor_data_streams" {
  name        = "${local.short_queue_prefix}-processingdata-stream"

  encryption_type = "KMS"
  kms_key_id      = data.aws_kms_key.existing_kinesis_encryption_key.arn
}
locals {
  new_kinesis_arn = aws_kinesis_stream.processor_data_streams.arn
}

