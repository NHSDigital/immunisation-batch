output "service_domain_name" {
  value = local.service_domain_name
}
output "batch_source_bucket" {
    value = aws_s3_bucket.batch_data_source_bucket.bucket
}
output "batch_destination_bucket" {
    value = aws_s3_bucket.batch_data_destination_bucket.bucket
}
output "sqs_queue_urls" {
    value = { for supplier, queue in aws_sqs_queue.fifo_queues : supplier => queue.id}
}