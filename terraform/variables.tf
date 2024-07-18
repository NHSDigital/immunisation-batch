variable "project_name" {
    default = "immunisations"
}

variable "project_short_name" {
    default = "imms"
}

variable "service" {
    default = "batch"
}

variable "region" {
    default = "eu-west-2"
}

variable "root_domain_name" {
    default = "dev.api.platform.nhs.uk"
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
    prefix              = "${var.project_name}-${var.service}-${var.environment}"
    short_prefix        = "${var.project_short_name}-${var.environment}"
    service_domain_name = "${var.environment}.${local.project_domain_name}"
  }