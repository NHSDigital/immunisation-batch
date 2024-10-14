"""Function to send the request to the Imms API (or return appropriate diagnostics if this is not possible)"""

from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
import requests
from immunisation_api import ImmunizationApi


cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


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
    Sends request to the Imms API (unless there was a failure at the recordprocessor level).
    Returns successful_api_response (bool indicating if a response in the 200s was received from the Imms API),
    any diagnostics, and the imms_id.
    """

    supplier = message_body.get("supplier")
    fhir_json = message_body.get("fhir_json")
    operation_requested = message_body.get("operation_requested")
    imms_id = message_body.get("imms_id")
    version = message_body.get("version")
    incoming_diagnostics = message_body.get("diagnostics")

    successful_api_response = False
    diagnostics = None

    if incoming_diagnostics:
        diagnostics = incoming_diagnostics

    elif operation_requested == "CREATE":
        response = immunization_api_instance.create_immunization(fhir_json, supplier)
        if response.status_code == 201:
            successful_api_response = True
            try:
                imms_id = response.headers.get("location").split("immunisation-fhir-api/Immunization/")[1]
            except (AttributeError, IndexError):
                imms_id = None
        else:
            diagnostics = get_operation_outcome_diagnostics(response)

    elif operation_requested == "UPDATE":
        fhir_json["id"] = imms_id
        response = immunization_api_instance.update_immunization(imms_id, version, fhir_json, supplier)
        if response.status_code == 200:
            successful_api_response = True
        else:
            diagnostics = get_operation_outcome_diagnostics(response)

    elif operation_requested == "DELETE":
        response = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier)
        if response.status_code == 204:
            successful_api_response = True
        else:
            diagnostics = get_operation_outcome_diagnostics(response)

    return successful_api_response, diagnostics, imms_id
