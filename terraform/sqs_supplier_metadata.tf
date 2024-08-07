resource "aws_sqs_queue" "fifo_queues" {
    name                      = "${local.short_queue_prefix}-file-processor-metadata-queue.fifo"
    fifo_queue                = true
    visibility_timeout_seconds = 30
    
    # Disable content-based deduplication - will process any records sent to queue
    content_based_deduplication  = false
}

# IAM Policy for Lambda to Access SQS
resource "aws_iam_policy" "lambda_sqs_policy" {
 name        = "lambda_sqs_policy"
 description = "Allows Lambda to access SQS"
 policy = jsonencode({
   Version = "2012-10-17"
   Statement = [
     {
       Action = [
         "sqs:ReceiveMessage",
         "sqs:DeleteMessage",
         "sqs:GetQueueAttributes",
       ]
       Resource = aws_sqs_queue.order_processing_queue.arn
       Effect   = "Allow"
     },
   ]
 })
}

