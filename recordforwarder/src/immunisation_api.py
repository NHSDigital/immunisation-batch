"""ImmunizationApi class for sending requests to the Imms API"""

import uuid
import logging
import requests
from models.authentication import AppRestrictedAuth
from utils_for_record_forwarder import get_environment

logger = logging.getLogger()


class ImmunizationApi:
    """Class for sending requests to the Imms API"""

    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator
        _env = get_environment()
        self.base_url = f"https://{_env if _env != 'prod' else ''}.api.service.nhs.uk/immunisation-fhir-api"

    def create_immunization(self, imms, supplier_system):
        """Sends a CREATE request to the Imms API"""
        return self._send("POST", "/Immunization", imms, None, supplier_system)

    def update_immunization(self, imms_id, version_id, imms, supplier_system):
        """Sends an UPDATE request to the Imms API"""
        return self._send("PUT", f"/Immunization/{imms_id}", imms, version_id, supplier_system)

    def delete_immunization(self, imms_id, imms, supplier_system):
        """Sends a DELETE request to the Imms API"""
        return self._send("DELETE", f"/Immunization/{imms_id}", imms, None, supplier_system)

    def _send(self, method: str, path: str, imms, version_id, supplier_system):
        access_token = self.authenticator.get_access_token()
        request_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Correlation-ID": str(uuid.uuid4()),
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
            "BatchSupplierSystem": supplier_system,
        }
        if version_id:
            request_headers["E-Tag"] = str(version_id)

        response = requests.request(
            method=method, url=f"{self.base_url}/{path}", json=imms, headers=request_headers, timeout=5
        )

        return response.text, response.status_code
