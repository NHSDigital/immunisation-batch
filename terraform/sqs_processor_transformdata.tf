# Define the Kinesis Data Stream resource with 15 shards
resource "aws_kinesis_stream" "processor_data_streams" {
  name        = "${local.short_queue_prefix}-processingdata-stream"
  shard_count = 15  
}

