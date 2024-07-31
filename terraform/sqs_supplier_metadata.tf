

resource "aws_sqs_queue" "fifo_queues" {
    for_each                  = toset(var.suppliers)
    name                      = "${local.prefix}-${each.key}-metadata-queue.fifo"
    fifo_queue                = true
    visibility_timeout_seconds = 30
    
    # Disable content-based deduplication - will process any records sent to queue
    content_based_deduplication  = false

tags = {
    supplier = each.key
}

}

