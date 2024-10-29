# Define the Kinesis Data Stream resource with 15 shards
resource "aws_kinesis_stream" "processor_data_streams" {
  name        = "${local.short_queue_prefix}-processingdata-stream"
  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }
}
locals {
  new_kinesis_arn = aws_kinesis_stream.processor_data_streams.arn
}

