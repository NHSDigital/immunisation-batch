import os
import logging
from s3_clients import dynamodb_client


logger = logging.getLogger()


def add_to_audit_table(message_id: str, file_key: str, created_at_formatted_str: str) -> bool:
    """Add the filename to the audit table"""
    try:
        dynamodb_client.put_item(
            TableName=os.environ["AUDIT_TABLE_NAME"],
            Item={
                "message_id": {"S": message_id},
                "filename": {"S": file_key},
                "status": {"S": "Processed"},
                "timestamp": {"S": created_at_formatted_str},
            },
        )
        logger.info("%s file, with message id %s, successfully added to audit table", file_key, message_id)
        return True
    except Exception:  # pylint: disable = broad-exception-caught
        return False
