resource "aws_dynamodb_table" "audit-table" {
    name         = "${local.short_prefix}-imms-batch-audit-table"
    billing_mode = "PAY_PER_REQUEST"
    hash_key     = "message_id"

    attribute {
        name = "message_id"
        type = "S"
    }

    attribute {
        name = "filename"
        type = "S"
    }

    attribute {
        name = "created_at"
        type = "S"
    }

    attribute {
        name = "status"
        type = "S"
    }

    global_secondary_index {
        name            = "filename_index"
        hash_key        = "filename"
        projection_type = "ALL"
    }

}