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

    def get_imms_id(self, identifier_system: str, identifier_value: str):
        return self._send("GET",
                          f"/Immunization?immunization.identifier={identifier_system}|{identifier_value}"
                          f"&_element=id,meta")

    def _send(self, method: str, path: str):
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
            headers=request_headers,
            timeout=5
        )
        logger.error(f"response: {response}")
        response_json = response.json()
        logger.error(f"response_json: {response_json}")
        if "total" in response_json:
            if response_json.get("total") == 1:
                return response_json, response.status_code
            else:
                return response_json, response.status_code
        else:
            return response_json, response.status_code
