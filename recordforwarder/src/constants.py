"""Constants for recordforwarder"""

IMMS_BATCH_APP_NAME = "Imms-Batch-App"


class Operations:
    """Class containing the CRUD operation lambdas which can be invoked by the batch process"""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"
