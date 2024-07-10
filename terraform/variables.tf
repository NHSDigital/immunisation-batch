variable "environment" { 
  description = "The environment to deploy (e.g., int, ref, internal-dev, prod)"
  type        = string
  default     = "internal-dev"  # Default to internal-dev if not specified
}

variable "ack_bucket_name" {
  description = "The name of the S3 bucket for acknowledgment files"
  type        = string
}

variable "int_account_id" {
  description = "AWS Account ID for the int environment"
  type        = string
}

variable "ref_account_id" {
  description = "AWS Account ID for the ref environment"
  type        = string
}

variable "internal_dev_account_id" {
  description = "AWS Account ID for the internal-dev environment"
  type        = string
}

variable "prod_account_id" {
  description = "AWS Account ID for the prod environment"
  type        = string
}
