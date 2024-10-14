"""Function to send the request to the Imms API (or return appropriate diagnostics if this is not possible)"""

import requests
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from immunisation_api import ImmunizationApi
from errors import MessageNotSuccessfulError


cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def send_create_request(fhir_json: dict, supplier: str) -> str:
    """Sends the create request and handles the response. Returns the imms_id."""
    response = immunization_api_instance.create_immunization(fhir_json, supplier)

    if response.status_code != 201:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(response))

    try:
        imms_id = response.headers.get("location").split("immunisation-fhir-api/Immunization/")[1]
    except (AttributeError, IndexError):
        imms_id = None
    return imms_id


def send_update_request(fhir_json: dict, supplier: str, imms_id: str, version: str) -> str:
    """Sends the update request and handles the response. Returns the imms_id."""
    fhir_json["id"] = imms_id
    response = immunization_api_instance.update_immunization(imms_id, version, fhir_json, supplier)

    if response.status_code != 200:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(response))

    return imms_id


def send_delete_request(fhir_json: dict, supplier: str, imms_id: str) -> str:
    """Sends the delete request and handles the response. Returns the imms_id."""
    response = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier)

    if response.status_code != 204:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(response))

    return imms_id


def get_operation_outcome_diagnostics(response: requests.Response) -> str:
    """
    Returns the diagnostics from the API response. If the diagnostics can't be found in the API response,
    returns a default diagnostics string
    """
    try:
        return response.json().get("issue")[0].get("diagnostics")
    except (requests.exceptions.JSONDecodeError, AttributeError, IndexError):
        return "Unable to obtain diagnostics from API response"


def send_request_to_api(message_body):
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level). Returns the imms id.
    If message is not successfully received and accepted by the Imms API raises a MessageNotSuccessful Error.
    """
    supplier = message_body.get("supplier")
    fhir_json = message_body.get("fhir_json")
    operation_requested = message_body.get("operation_requested")
    imms_id = message_body.get("imms_id")
    version = message_body.get("version")
    incoming_diagnostics = message_body.get("diagnostics")

    if incoming_diagnostics:
        raise MessageNotSuccessfulError(incoming_diagnostics)

    if operation_requested == "CREATE":
        return send_create_request(fhir_json, supplier)

    if operation_requested == "UPDATE":
        return send_update_request(fhir_json, supplier, imms_id, version)

    if operation_requested == "DELETE":
        return send_delete_request(fhir_json, supplier, imms_id)
