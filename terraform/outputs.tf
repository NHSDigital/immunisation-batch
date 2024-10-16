output "batch_source_bucket" {
    value = aws_s3_bucket.batch_data_source_bucket.bucket
}
output "batch_destination_bucket" {
    value = aws_s3_bucket.batch_data_destination_bucket.bucket
}
