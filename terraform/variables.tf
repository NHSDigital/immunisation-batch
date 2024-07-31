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

variable "suppliers" {
    description = "List of supplier names"
    type        = list(string)
    default = [
        "EMIS", "PINNACLE", "SONAR", "TPP",
    "AGEM-NIVS", "NIMS", "EVA", "RAVS", "MEDICAL_DIRECTOR",
    "WELSH_DA_1", "WELSH_DA_2", "NORTHERN_IRELAND_DA",
    "SCOTLAND_DA", "COVID19_VACCINE_RESOLUTION_SERVICEDESK"
    ]

}