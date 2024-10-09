from typing import Union


ack_headers = [
    "MESSAGE_HEADER_ID",
    "HEADER_RESPONSE_CODE",
    "ISSUE_SEVERITY",
    "ISSUE_CODE",
    "RESPONSE_TYPE",
    "RESPONSE_CODE",
    "RESPONSE_DISPLAY",
    "RECEIVED_TIME",
    "MAILBOX_FROM",
    "LOCAL_ID",
    "MESSAGE_DELIVERY",
]


def create_ack_data(
    created_at_formatted_string: str, row_id: str, delivered: bool, response_code, diagnostics: Union[None, str] = None
) -> dict:
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    return {
        "MESSAGE_HEADER_ID": row_id,
        "HEADER_RESPONSE_CODE": "fatal-error" if diagnostics else "ok",
        "ISSUE_SEVERITY": "error" if diagnostics else "information",
        "ISSUE_CODE": "error" if diagnostics else "informational",
        "RESPONSE_TYPE": "business",
        "RESPONSE_CODE": (
            "20005" if diagnostics else "20013"
        ),  # 20007 if duplicate, 20009 if payload validation failure, else 2005
        "RESPONSE_DISPLAY": diagnostics if diagnostics else "Success",
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "TBC",
        "LOCAL_ID": "DPS",
        "MESSAGE_DELIVERY": delivered,
    }
