variable "project_name" {
    default = "immunisation-batch"
}

variable "project_short_name" {
    default = "imms-batch"
}

variable "service" {
    default = "batch"
}

data "aws_vpc" "default" {
    default = true
}
data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}

locals {
    environment         = terraform.workspace
    prefix              = "${var.project_name}-${local.environment}"
    short_prefix        = "${var.project_short_name}-${local.environment}"
    short_queue_prefix  = "${var.project_short_name}-${local.environment}"
    policy_path = "${path.root}/policies"
    is_temp = length(regexall("[a-z]{2,4}-?[0-9]+", local.environment)) > 0
    account_id = local.environment == "prod" ? 232116723729 : 603871901111
    local_account_id = local.environment == "prod" ? 664418956997 : 345594581768
    config_bucket = local.environment == "prod" ? "prod" : "internal-dev"
    splunk_env = local.environment == "prod" ? "prod" : local.environment == "int" ? "int" : local.environment == "ref" ? "ref" : "internal-dev"
    config_env = local.environment == "prod" ? "prod" : "internal-dev"
    api_env = local.environment == "prod" ? "prod" : local.environment == "int" ? "int" : local.environment == "ref" ? "ref" : "internal-dev"
    
    tags = {
        Project     = var.project_name
        Environment = local.environment
        Service     = var.service
    }
}

variable "aws_region" {
    default = "eu-west-2"
}

data "aws_elasticache_cluster" "existing_redis" {
  cluster_id = "immunisation-redis-cluster"
}

data "aws_security_group" "existing_sg" {
  filter {
    name   = "group-name"
    values = ["immunisation-security-group"]
  }
}

data "aws_s3_bucket" "existing_bucket" {
  bucket = "imms-${local.config_env}-supplier-config"
}
data "aws_kinesis_firehose_delivery_stream" "splunk_stream" {
  name = "immunisation-fhir-api-${local.splunk_env}-splunk-firehose"
}

data "aws_lambda_function" "existing_create_lambda" {
  function_name = "imms-${local.api_env}_create_imms"
}

data "aws_lambda_function" "existing_delete_lambda" {
  function_name = "imms-${local.api_env}_delete_imms"
}

data "aws_lambda_function" "existing_update_lambda" {
  function_name = "imms-${local.api_env}_update_imms"
}

data "aws_lambda_function" "existing_search_lambda" {
  function_name = "imms-${local.api_env}_search_imms"
}
data "aws_kms_key" "existing_s3_encryption_key" {
  key_id = "alias/imms-batch-s3-shared-key"
}
data "aws_kms_key" "existing_lambda_encryption_key" {
  key_id = "alias/imms-batch-lambda-env-encryption"
}
data "aws_kms_key" "existing_kinesis_encryption_key" {
  key_id = "alias/imms-batch-kinesis-stream-encryption"
}