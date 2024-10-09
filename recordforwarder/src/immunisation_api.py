import requests
import uuid
import logging
from models.authentication import AppRestrictedAuth
from utils_for_record_forwarder import get_environment

logger = logging.getLogger()


class ImmunizationApi:
    def __init__(self, authenticator: AppRestrictedAuth):
        self.authenticator = authenticator
        environment = get_environment()
        self.base_url = (
            f"https://{environment}.api.service.nhs.uk/immunisation-fhir-api"
            if environment != "prod"
            else "https://api.service.nhs.uk/immunisation-fhir-api"
        )

    def create_immunization(self, imms, supplier_system):
        return self._send("POST", "/Immunization", imms, None, supplier_system)

    def update_immunization(self, imms_id, version_id, imms, supplier_system):
        print(f"imms_id:{imms_id}")
        print(f"version_id:{version_id}")
        return self._send("PUT", f"/Immunization/{imms_id}", imms, version_id, supplier_system)

    def delete_immunization(self, imms_id, imms, supplier_system):
        print(f"imms_id:{imms_id}")
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
        # Conditionally add the "E-Tag" header if version_id is present
        if version_id:
            request_headers["E-Tag"] = str(version_id)
        response = requests.request(
            method=method, url=f"{self.base_url}/{path}", json=imms, headers=request_headers, timeout=5
        )
        return response.text, response.status_code
