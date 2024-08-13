

resource "aws_sqs_queue" "fifo_queues" {
    for_each                  = toset(var.suppliers)
    name                      = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-metadata-queue.fifo"
    fifo_queue                = true
    visibility_timeout_seconds = 30
    
    # TO DO - enable content-based deduplication - will not record duplicate body sent to queue
    content_based_deduplication  = true

tags = {
    supplier = each.key
}

}

