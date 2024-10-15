data "aws_vpc" "default" {
    default = true
}
data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}
data "aws_route_tables" "default_route_tables" {
  vpc_id = data.aws_vpc.default.id
}

variable "aws_region" {
    default = "eu-west-2"
}