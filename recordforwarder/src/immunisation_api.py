import requests
import uuid
import logging
from models.authentication import AppRestrictedAuth
from models.env import get_environment

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

    def create_immunization(self, imms):
        return self._send(
            "POST",
            "/Immunization",
            imms,
            None

        )

    def update_immunization(self, imms_id, version_id, imms):
        print(f"imms_id:{imms_id}")
        print(f"version_id:{version_id}")
        return self._send(
            "PUT",
            f"/Immunization/{imms_id}",
            imms,
            version_id
        )

    def delete_immunization(self, imms_id, imms):
        print(f"imms_id:{imms_id}")
        return self._send(
            "DELETE",
            f"/Immunization/{imms_id}",
            imms,
            None
        )

    def _send(self, method: str, path: str, imms, version_id):
        print("send_started")
        print(f"version_id:{version_id}")
        access_token = self.authenticator.get_access_token()
        logger.debug(f"Access token obtained: {access_token}")
        print(f"access_token:{access_token}")
        if version_id:
            request_headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Request-ID': str(uuid.uuid4()),
                'X-Correlation-ID': str(uuid.uuid4()),
                "Content-Type": "application/fhir+json",
                "Accept": "application/fhir+json",
                "E-Tag": str(version_id)
                }
        else:
            request_headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Request-ID': str(uuid.uuid4()),
                'X-Correlation-ID': str(uuid.uuid4()),
                "Content-Type": "application/fhir+json",
                "Accept": "application/fhir+json",
            }
        print(f"request_headers:{request_headers}")
        response = requests.request(
            method=method,
            url=f"{self.base_url}/{path}",
            json=imms,
            headers=request_headers,
            timeout=5
        )
        logger.error(f"response: {response}")
        logger.error(f"response_json: {response.text}")
        return response.text, response.status_code
