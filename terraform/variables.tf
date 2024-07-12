variable "project_name" {
    default = "immunisations"
}

variable "project_short_name" {
    default = "imms"
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
    root_domain = "dev.api.platform.nhs.uk"
}

locals {
    project_domain_name = data.aws_route53_zone.project_zone.name
}

locals {
    environment         = terraform.workspace
    prefix              = "${var.project_name}-${var.service}-${local.environment}"
    short_prefix        = "${var.project_short_name}-${local.environment}"
    service_domain_name = "${local.environment}.${local.project_domain_name}"

    tags = {
        Project     = var.project_name
        Environment = local.environment
        Service     = var.service
    }
}

variable "region" {
    default = "eu-west-2"
}

variable "root_domain_name" {
    default = "dev.api.platform.nhs.uk"
}
variable "int_account_id" {
  default = "790083933819"
}

variable "ref_account_id" {
  default = "790083933819"
}

variable "internal_dev_account_id" {
  default = "790083933819"
}

variable "sandbox_account_id" {
  default = "790033819"
}

variable "prod_account_id" {
  default = "790033819"
}

locals {
  environment         = terraform.workspace
  prefix              = "${var.project_name}-${var.service}-${local.environment}"
  short_prefix        = "${var.project_short_name}-${local.environment}"
  service_domain_name = "${local.environment}.${local.project_domain_name}"

  tags = {
    Project     = var.project_name
    Environment = local.environment
    Service     = var.service
  }

  ack_bucket_name = "immunisation-fhir-api-${local.environment}-batch-data-destination"

  account_ids = {
    "int"           = var.int_account_id
    "ref"           = var.ref_account_id
    "internal-dev"  = var.internal_dev_account_id
    "sandbox"       =var.sandbox_account_id
    "prod"          = var.prod_account_id
  }

  account_id = lookup(local.account_ids, local.environment, var.internal_dev_account_id)
}

provider "aws" {
  region = "eu-west-2"
}
