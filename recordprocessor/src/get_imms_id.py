"""ImmunizationApi class for sending GET request to Imms API to obtain id and version"""

import uuid
import logging
import requests
from typing import Tuple
from models.authentication import AppRestrictedAuth
from utils_for_recordprocessor import get_environment

logger = logging.getLogger()


class ImmunizationApi:
    """Class for sending GET request to Imms API to obtain id and version"""

    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator
        _env = get_environment()
        self.base_url = f"https://{_env if _env != 'prod' else ''}.api.service.nhs.uk/immunisation-fhir-api"

    def get_imms_id(self, identifier_system: str, identifier_value: str):
        """Send a GET request to Imms API requesting the id and version"""
        return self._send(
            "GET", f"/Immunization?immunization.identifier={identifier_system}|{identifier_value}&_element=id,meta"
        )

    def _send(self, method: str, path: str) -> Tuple[dict, int]:
        access_token = self.authenticator.get_access_token()
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Correlation-ID": str(uuid.uuid4()),
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
        }
        response = requests.request(method=method, url=f"{self.base_url}/{path}", headers=request_headers, timeout=5)
        logger.info("response: %s", response)
        response_json = response.json()
        return response_json, response.status_code
