

resource "aws_sqs_queue" "processor_fifo_queues" {
    for_each                  = toset(var.suppliers)
    name                      = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-processingdata-queue.fifo"
    fifo_queue                = true
    visibility_timeout_seconds = 60
    
    # TO DO - enable content-based deduplication - will not record duplicate body sent to queue
    content_based_deduplication  = true

tags = {
    supplier = each.key
}

}
data "aws_sqs_queue" "processingqueues" {
  for_each = toset(var.suppliers)
  name     = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-processingdata-queue.fifo"

  # Ensure the queue exists before looking it up
  depends_on = [aws_sqs_queue.processor_fifo_queues]
}

locals {
  new_sqs_arns = [for queue in data.aws_sqs_queue.processingqueues : queue.arn]
}

