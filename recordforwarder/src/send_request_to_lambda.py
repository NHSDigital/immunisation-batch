"""Function to send the request directly to lambda (or return appropriate diagnostics if this is not possible)"""

from errors import MessageNotSuccessfulError, IdNotFoundError
from get_imms_id_and_version import get_imms_id_and_version
from clients import lambda_client
from utils_for_record_forwarder import invoke_lambda
from constants import Constants
from decrpyt_key import decrypt_key


def send_create_request(fhir_json: dict, supplier: str) -> str:
    """Sends the create request and handles the response. Returns the imms_id."""
    # Send create request
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME, "BatchSupplierSystem": supplier}
    payload = {"headers": headers, "body": fhir_json}
    create_lambda_name = decrypt_key("CREATE_LAMBDA_NAME")
    status_code, body, headers = invoke_lambda(lambda_client, create_lambda_name, payload)
    if status_code != 201:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(body))

    # Return imms id (default to None if unable to find the id)
    return headers.get("Location").split("/")[-1] or None


def send_update_request(fhir_json: dict, supplier: str) -> str:
    """Obtains the imms_id, sends the update request and handles the response. Returns the imms_id."""
    # Obtain imms_id and version
    try:
        imms_id, version = get_imms_id_and_version(fhir_json)
    except IdNotFoundError as error:
        raise MessageNotSuccessfulError(error) from error
    if not imms_id:
        raise MessageNotSuccessfulError("Unable to obtain Imms ID")
    if not version:
        raise MessageNotSuccessfulError("Unable to obtain Imms version")

    # Send update request
    fhir_json["id"] = imms_id
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME, "BatchSupplierSystem": supplier, "E-Tag": version}
    payload = {"headers": headers, "body": fhir_json, "pathParameters": {"id": imms_id}}
    update_lambda_name = decrypt_key("UPDATE_LAMBDA_NAME")
    status_code, body, _ = invoke_lambda(lambda_client, update_lambda_name, payload)
    if status_code != 200:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(body))

    return imms_id


def send_delete_request(fhir_json: dict, supplier: str) -> str:
    """Sends the delete request and handles the response. Returns the imms_id."""
    # Obtain imms_id
    try:
        imms_id, _ = get_imms_id_and_version(fhir_json)
    except IdNotFoundError as error:
        raise MessageNotSuccessfulError(error) from error
    if not imms_id:
        raise MessageNotSuccessfulError("Unable to obtain Imms ID")

    # Send delete request
    headers = {"SupplierSystem": Constants.IMMS_BATCH_APP_NAME, "BatchSupplierSystem": supplier}
    payload = {"headers": headers, "body": fhir_json, "pathParameters": {"id": imms_id}}
    delete_lambda_name = decrypt_key("DELETE_LAMBDA_NAME")
    status_code, body, _ = invoke_lambda(lambda_client, delete_lambda_name, payload)
    if status_code != 204:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(body))

    return imms_id


def get_operation_outcome_diagnostics(body: dict) -> str:
    """
    Returns the diagnostics from the API response. If the diagnostics can't be found in the API response,
    returns a default diagnostics string
    """
    try:
        return body.get("issue")[0].get("diagnostics")
    except (AttributeError, IndexError):
        return "Unable to obtain diagnostics from API response"


def send_request_to_lambda(message_body: dict) -> str:
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level). Returns the imms id.
    If message is not successfully received and accepted by the Imms API raises a MessageNotSuccessful Error.
    """
    if incoming_diagnostics := message_body.get("diagnostics"):
        raise MessageNotSuccessfulError(incoming_diagnostics)

    supplier = message_body.get("supplier")
    fhir_json = message_body.get("fhir_json")
    operation_requested = message_body.get("operation_requested")

    # Send request to Imms FHIR API and return the imms_id
    function_map = {"CREATE": send_create_request, "UPDATE": send_update_request, "DELETE": send_delete_request}
    return function_map[operation_requested](fhir_json=fhir_json, supplier=supplier)
