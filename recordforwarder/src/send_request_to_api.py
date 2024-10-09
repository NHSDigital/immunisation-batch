"""Function to send the request to the Imms API (or return appropriate diagnostics if this is not possible)"""

import re
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from immunisation_api import ImmunizationApi
from ods_patterns import ODS_PATTERNS


cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def identify_supplier(file_key: str):
    """Identify the supplier using the ODS code in the file name"""
    supplier_match = re.search(r"_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$", file_key)
    ods_code = supplier_match.group(1).upper() if supplier_match else None
    return ODS_PATTERNS.get(ods_code, None)


def send_request_to_api(message_body):
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level).
    Returns message_delivered (bool indicating if a response in the 200s was received from the Imms API),
    response_code (for ack file) and any diagnostics.
    """

    fhir_json = message_body.get("fhir_json")
    action_flag = message_body.get("action_flag")
    file_key = message_body.get("file_name")
    imms_id = message_body.get("imms_id")
    version = message_body.get("version")

    message_delivered = False
    diagnostics = None
    response_code = None

    for _ in range(1):
        if fhir_json == "No_Permissions":
            diagnostics = "Skipped As No permissions for operation"
            response_code = "20005"
            break

        if imms_id == "None" and version == "None":
            diagnostics = "failed in json conversion"
            response_code = "20005"
            break

        supplier_system = identify_supplier(file_key)

        if action_flag == "new":
            response, status_code = immunization_api_instance.create_immunization(fhir_json, supplier_system)
            print(f"response:{response},status_code:{status_code}")
            if status_code == 201:
                response_code = "20013"
                message_delivered = True
            elif status_code == 422:
                diagnostics = "Duplicate Message received"
                response_code = "20007"
            else:
                diagnostics = "Payload validation failure"
                response_code = "20009"

        elif action_flag == "update" and imms_id not in (None, "None") and version not in (None, "None"):
            fhir_json["id"] = imms_id
            response, status_code = immunization_api_instance.update_immunization(
                imms_id, version, fhir_json, supplier_system
            )
            print(f"response:{response},status_code:{status_code}")
            if status_code == 200:
                response_code = "20013"
            else:
                diagnostics = "Payload validation failure"
                response_code = "20009"

        elif action_flag == "delete" and imms_id not in (None, "None"):
            response, status_code = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier_system)
            print(f"response:{response},status_code:{status_code}")
            if status_code == 204:
                response_code = "20013"
                message_delivered = True
            else:
                diagnostics = "Payload validation failure"
                response_code = "20009"

    return message_delivered, response_code, diagnostics
