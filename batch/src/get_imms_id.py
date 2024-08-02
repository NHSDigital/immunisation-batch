import requests
import uuid

from models.authentication import AppRestrictedAuth


class ImmunizationApi:
    def __init__(self, authenticator: AppRestrictedAuth, environment):
        self.authenticator = authenticator

        self.base_url = f"https://{environment}.api.service.nhs.uk/immunisation-fhir-api" \
            if environment != "prod" else "https://api.service.nhs.uk/immunisation-fhir-api"

    def get_immunization_id(self, identifier_system, identifier_value):
        return self._send("GET", f"Immunization/{identifier_value}", identifier_system, identifier_value)

    def _send(self, method, path, identifier_system, identifier_value):
        access_token = self.authenticator.get_access_token()
        request_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Request-ID': str(uuid.uuid4()),
            'X-Correlation-ID': str(uuid.uuid4()),
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json",
            "identifierSystem": identifier_system
        }
        response = requests.request(method=method, url=f"{self.base_url}/{path}", headers=request_headers, timeout=5)

        if response.status_code == 200:
            return response
        else:
            return {
                "request": f"{identifier_system}#{identifier_value}",
                "response_text": response.text,
                "status_code": response.status_code
            }
