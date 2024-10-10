"""Function to send the request to the Imms API (or return appropriate diagnostics if this is not possible)"""

import re
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from immunisation_api import ImmunizationApi


cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def send_request_to_api(message_body):
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level).
    Returns message_delivered (bool indicating if a response in the 200s was received from the Imms API),
    response_code (for ack file) and any diagnostics.
    """

    fhir_json = message_body.get("fhir_json")
    operation_requested = message_body.get("operation_requested")
    supplier_system = message_body.get("supplier")
    imms_id = message_body.get("imms_id")
    version = message_body.get("version")
    incoming_diagnostics = message_body.get("diagnostics")

    message_delivered = False
    diagnostics = None
    response_code = None

    if incoming_diagnostics:
        response_code = "20005"
        if incoming_diagnostics == "No permissions for operation":
            diagnostics = "Skipped As No permissions for operation"
        elif incoming_diagnostics == "Unsupported file type received as an attachment":
            diagnostics = "failed in json conversion or obtaining imms_id and version"
        elif incoming_diagnostics == "Unable to obtain imms_id":
            diagnostics = incoming_diagnostics
        elif incoming_diagnostics == "Unable to obtain version":
            diagnostics = incoming_diagnostics

    elif operation_requested == "CREATE":
        _, status_code = immunization_api_instance.create_immunization(fhir_json, supplier_system)
        if status_code == 201:
            response_code = "20013"
            message_delivered = True
        elif status_code == 422:
            diagnostics = "Duplicate Message received"
            response_code = "20007"
        else:
            diagnostics = "Payload validation failure"
            response_code = "20009"

    elif operation_requested == "UPDATE" and imms_id not in (None, "None") and version not in (None, "None"):
        fhir_json["id"] = imms_id
        _, status_code = immunization_api_instance.update_immunization(imms_id, version, fhir_json, supplier_system)
        if status_code == 200:
            response_code = "20013"
        else:
            diagnostics = "Payload validation failure"
            response_code = "20009"

    elif operation_requested == "DELETE" and imms_id not in (None, "None"):
        _, status_code = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier_system)
        if status_code == 204:
            response_code = "20013"
            message_delivered = True
        else:
            diagnostics = "Payload validation failure"
            response_code = "20009"

    return message_delivered, response_code, diagnostics
