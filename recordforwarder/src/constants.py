class Constants:
    """A class to hold various constants used in the application."""

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



    def data_rows(status, created_at_formatted, message_header):

        if status is True:
            data_row = [
                message_header,
                "ok",
                "information",
                "informational",
                "business",
                "20013",
                "Success",
                created_at_formatted,
                "TBC",
                "DPS",
                True,
            ]
            return data_row
        elif status == "duplicate":
            data_row = [
                message_header,
                "fatal-error",
                "error",
                "error",
                "business",
                "20007",
                "Duplicate Message received",
                created_at_formatted,
                "TBC",
                "DPS",
                False,
            ]
            return data_row
        elif status == "no permissions":
            data_row = [
                message_header,
                "fatal-error",
                "error",
                "error",
                "business",
                "20005",
                "Skipped As No permissions for operation",
                created_at_formatted,
                "TBC",
                "DPS",
                False,
            ]  # noqa: E501
            return data_row
        if status == "None":
            data_row = [
                message_header,
                "fatal-error",
                "error",
                "error",
                "business",
                "20005",
                "failed in json conversion",
                created_at_formatted,
                "TBC",
                "DPS",
                False,
            ]  # noqa: E501
            return data_row
        if status is False:
            data_row = [
                message_header,
                "fatal-error",
                "error",
                "error",
                "business",
                "20009",
                "Payload validation failure",
                created_at_formatted,
                "TBC",
                "DPS",
                False,
            ]  # noqa: E501
            return data_row
