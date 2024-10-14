"""Constants for recordprocessor"""


class Constants:
    """Constants for recordprocessor"""

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


class Diagnostics:
    """Diagnostics messages"""

    NO_PERMISSIONS = "No permissions for requested operation"
    MISSING_UNIQUE_ID = "UNIQUE_ID or UNIQUE_ID_URI is missing"
    UNABLE_TO_OBTAIN_IMMS_ID = "Unable to obtain imms event id"
    UNABLE_TO_OBTAIN_VERSION = "Unable to obtain current imms event version"
    INVALID_CONVERSION = "Unable to convert row to FHIR Immunization Resource JSON format"
