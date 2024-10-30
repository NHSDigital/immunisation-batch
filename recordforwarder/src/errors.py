"""Custom errors for recordforwarder"""


class MessageNotSuccessfulError(Exception):
    """
    Generic error message for any scenario which either prevents sending to the Imms API, or which results in a
    non-successful response from the Imms API
    """

    def __init__(self, message=None):
        self.message = message


class IdNotFoundError(Exception):
    """Error message for when the imms event id could not be found by the Imms FHIR API search lambda"""

    def __init__(self, message=None):
        self.message = message
