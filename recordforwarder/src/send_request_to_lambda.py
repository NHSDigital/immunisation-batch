"""Function to send the request directly to lambda (or return appropriate diagnostics if this is not possible)"""

import os
from errors import MessageNotSuccessfulError, IdNotFoundError
from get_imms_id_and_version import get_imms_id_and_version
from utils_for_record_forwarder import invoke_lambda
from constants import IMMS_BATCH_APP_NAME


CREATE_LAMBDA_NAME = os.getenv("CREATE_LAMBDA_NAME")
UPDATE_LAMBDA_NAME = os.getenv("UPDATE_LAMBDA_NAME")
DELETE_LAMBDA_NAME = os.getenv("DELETE_LAMBDA_NAME")


def send_create_request(fhir_json: dict, supplier: str, file_key: str, row_id: str):
    """Sends the create request."""
    # Send create request
    headers = {
        "SupplierSystem": IMMS_BATCH_APP_NAME,
        "BatchSupplierSystem": supplier,
        "Filename": file_key,
        "MessageId": row_id,
    }
    payload = {"headers": headers, "body": fhir_json}
    invoke_lambda(CREATE_LAMBDA_NAME, payload)


def send_update_request(fhir_json: dict, supplier: str, file_key: str, row_id: str):
    """Obtains the imms_id, sends the update request."""
    # Obtain imms_id and version
    try:
        imms_id, version = get_imms_id_and_version(fhir_json)
    except IdNotFoundError as error:
        raise MessageNotSuccessfulError(error) from error
    if not imms_id:
        raise MessageNotSuccessfulError("Unable to obtain Imms id")
    if not version:
        raise MessageNotSuccessfulError("Unable to obtain Imms version")

    # Send update request
    fhir_json["id"] = imms_id
    headers = {
        "SupplierSystem": IMMS_BATCH_APP_NAME,
        "BatchSupplierSystem": supplier,
        "E-Tag": version,
        "Filename": file_key,
        "MessageId": row_id,
    }
    payload = {"headers": headers, "body": fhir_json, "pathParameters": {"id": imms_id}}
    invoke_lambda(UPDATE_LAMBDA_NAME, payload)


def send_delete_request(fhir_json: dict, supplier: str, file_key: str, row_id: str):
    """Obtains the imms_id, sends the delete request."""
    # Obtain imms_id
    try:
        imms_id, _ = get_imms_id_and_version(fhir_json)
    except IdNotFoundError as error:
        raise MessageNotSuccessfulError(error) from error
    if not imms_id:
        raise MessageNotSuccessfulError("Unable to obtain Imms ID")

    # Send delete request
    headers = {
        "SupplierSystem": IMMS_BATCH_APP_NAME,
        "BatchSupplierSystem": supplier,
        "Filename": file_key,
        "MessageId": row_id,
    }
    payload = {"headers": headers, "body": fhir_json, "pathParameters": {"id": imms_id}}
    invoke_lambda(DELETE_LAMBDA_NAME, payload)


def send_request_to_lambda(message_body: dict):
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level). Returns the imms id.
    If message is not successfully received and accepted by the Imms API raises a MessageNotSuccessful Error.
    """
    if incoming_diagnostics := message_body.get("diagnostics"):
        raise MessageNotSuccessfulError(incoming_diagnostics)

    supplier = message_body.get("supplier")
    fhir_json = message_body.get("fhir_json")
    file_key = message_body.get("file_key")
    row_id = message_body.get("row_id")
    operation_requested = message_body.get("operation_requested")

    # Send request to Imms FHIR API and return the imms_id
    function_map = {"CREATE": send_create_request, "UPDATE": send_update_request, "DELETE": send_delete_request}
    function_map[operation_requested](fhir_json=fhir_json, supplier=supplier, file_key=file_key, row_id=row_id)
