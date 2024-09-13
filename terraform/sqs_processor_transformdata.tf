resource "aws_kinesis_stream" "processor_streams" {
  for_each            = toset(var.suppliers)
  name                = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-processingdata-stream"
  shard_count         = var.default_shard_count

  # Tags to identify the stream based on supplier
  tags = {
    supplier = each.key
  }
}

