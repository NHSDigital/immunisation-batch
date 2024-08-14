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

variable "suppliers" {
  description = "List of supplier names. 5 extra pipelines"
  type        = list(string)
  default     = [
    "EMIS", "PINNACLE", "SONAR", "TPP",
    "AGEM-NIVS", "NIMS", "EVA", "RAVS", "MEDICAL_DIRECTOR",
    "WELSH_DA_1", "WELSH_DA_2", "NORTHERN_IRELAND_DA",
    "SCOTLAND_DA", "COVID19_VACCINE_RESOLUTION_SERVICEDESK"
  ]
}

variable "supplier_name_map" { 
  description = "Mapping of long supplier names to shorter names"
  type        = map(string)
  default     = {
    "EMIS"                  = "EMIS"
    "PINNACLE"              = "PINN"
    "SONAR"                 = "SONAR"
    "TPP"                   = "TPP"
    "AGEM-NIVS"             = "AGEM_NIVS"
    "NIMS"                  = "NIMS"
    "EVA"                   = "EVA"
    "RAVS"                  = "RAVS"
    "MEDICAL_DIRECTOR"      = "M_D"
    "WELSH_DA_1"            = "WELSHDA1"
    "WELSH_DA_2"            = "WELSHDA2"
    "NORTHERN_IRELAND_DA"   = "NIREDA"
    "SCOTLAND_DA"           = "SCOTDA"
    "COVID19_VACCINE_RESOLUTION_SERVICEDESK" = "C19VAX_SRVCEDSK"
  }
}

# Data source to get SQS queue ARNs
data "aws_sqs_queue" "queues" {
  for_each = toset(var.suppliers)
  name     = "${local.short_queue_prefix}-${lookup(var.supplier_name_map, each.key)}-metadata-queue.fifo"
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
  root_domain          = var.root_domain_name
  project_domain_name  = "" # This should be populated if using AWS Route 53, or remove if not needed
  environment          = terraform.workspace
  prefix               = "${var.project_name}-${var.service}-${local.environment}"
  short_prefix         = "${var.project_short_name}-${local.environment}"
  short_queue_prefix   = "${var.project_short_name}-${var.service}-${local.environment}"
  service_domain_name  = "${local.environment}.${local.project_domain_name}"

  tags = {
    Project     = var.project_name
    Environment = local.environment
    Service     = var.service
  }

  # Calculate the ARNs of existing SQS queues
  existing_sqs_arns = [for queue in data.aws_sqs_queue.queues : queue.arn]
}

# Local Account ID variable (Assuming it's retrieved or set elsewhere in the code)
variable "local_account_id" {
  description = "The local AWS account ID"
  type        = string
}

# Account ID for production environment
variable "account_id" {
  description = "AWS Account ID for the production environment"
  type        = string
}

# Environment variable
variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
}

# Usage example for existing_sqs_arns
resource "some_aws_resource" "example" {
  sqs_arns = local.existing_sqs_arns
}
