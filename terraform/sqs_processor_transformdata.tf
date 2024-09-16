# Define the Kinesis Data Stream resource
resource "aws_kinesis_stream" "processor_data_streams" {
  for_each            = toset(var.suppliers)
  name                = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-processingdata-stream"
  shard_count         = 1

# Tags to identify the stream based on supplier
  tags = {
    supplier = each.key
  }
}

# Kinesis Data Stream lookup
data "aws_kinesis_stream" "processingstreams" {
  for_each = toset(var.suppliers)
  name     = "${local.short_stream_prefix}-${lookup(var.supplier_name_map, each.key)}-processingdata-stream"

  # Ensure the stream exists before looking it up
  depends_on = [aws_kinesis_stream.processor_data_streams]
}

locals {
  new_kinesis_arns = [for stream in data.aws_kinesis_stream.processingstreams : stream.arn]
}
