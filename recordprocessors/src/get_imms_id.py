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

    def create_imms(self, imms):
        print("started")
        print(f"imms:{imms}")
        return self._send(
            "POST",
            "/Immunization",
            imms
        )

    def _send(self, method: str, path: str, imms):
        print("send_started")
        access_token = self.authenticator.get_access_token()
        logger.debug(f"Access token obtained: {access_token}")
        print(f"access_token:{access_token}")
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
        print(f"response:{response}")
        logger.debug(f"Response received: {response}")

        if response.status_code == 201:
            return response.text, response.status_code
        else:
            return response.text, response.status_code
