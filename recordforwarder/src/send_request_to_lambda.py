"""Function to send the request directly to lambda (or return appropriate diagnostics if this is not possible)"""

import json
import os
import requests
from errors import MessageNotSuccessfulError
import boto3


client = boto3.client('lambda')
create_lambda_name = os.getenv('CREATE_LAMBDA_NAME')
update_lambda_name = os.getenv('UPDATE_LAMBDA_NAME')
delete_lambda_name = os.getenv('DELETE_LAMBDA_NAME')


def send_create_request(fhir_json: dict, supplier: str) -> str:
    """Sends the create request and handles the response. Returns the imms_id."""
    # Prepare the payload
    payload = {
        'headers': {
                      'SupplierSystem': 'Imms-Batch-App',
                      'BatchSupplierSystem': supplier
                   },
        'body': fhir_json
    }
    # Invoke the target Lambda function
    response = client.invoke(
        FunctionName=create_lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    response_payload = json.loads(response['Payload'].read())
    if response_payload.get("statusCode") != 201:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(response_payload))

    try:
        imms_headers = response_payload.get("headers")
        imms_id = imms_headers['Location'].split('/')[-1]
    except (AttributeError, IndexError):
        imms_id = None
    return imms_id


def send_update_request(fhir_json: dict, supplier: str, imms_id: str, version: str) -> str:
    """sends the update request and handles the response. returns the imms_id."""
    fhir_json["id"] = imms_id
    payload = {
        'headers': {
                      'SupplierSystem': 'Imms-Batch-App',
                      'BatchSupplierSystem': supplier,
                      'E-Tag': version
                   },
        'body': fhir_json,
        'pathParameters': { 
                            'id': imms_id
                          }
    }
    # Invoke the target Lambda function
    response = client.invoke(
        FunctionName=update_lambda_name,
        InvocationType='RequestResponse',  # Change to 'Event' for asynchronous invocation
        Payload=json.dumps(payload)
    )
    response_payload = json.loads(response['Payload'].read())
    if response_payload.get("statusCode") != 200:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(response_payload))

    return imms_id


def send_delete_request(fhir_json: dict, supplier: str, imms_id: str) -> str:
    """Sends the delete request and handles the response. Returns the imms_id."""
    payload = {
        'headers': {
                      'SupplierSystem': 'Imms-Batch-App',
                      'BatchSupplierSystem': supplier
                   },
        'body': fhir_json,
        'pathParameters': { 
                            'id': imms_id
                          }
    }
    # Invoke the target Lambda function
    response = client.invoke(
        FunctionName=delete_lambda_name,
        InvocationType='RequestResponse',  # Change to 'Event' for asynchronous invocation
        Payload=json.dumps(payload)
    )
    response_payload = json.loads(response['Payload'].read())
    if response_payload.get("statusCode") != 204:
        raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(response_payload))

    return imms_id


def get_operation_outcome_diagnostics(response: requests.Response) -> str:
    """
    Returns the diagnostics from the API response. If the diagnostics can't be found in the API response,
    returns a default diagnostics string
    """
    try:
        return response.json().get("issue")[0].get("diagnostics")
    except (requests.exceptions.JSONDecodeError, AttributeError, IndexError):
        return "Unable to obtain diagnostics from API response"


def send_request_to_lambda(message_body):
    """
    Sends request to the Imms API (unless there was a failure at the recordprocessor level). Returns the imms id.
    If message is not successfully received and accepted by the Imms API raises a MessageNotSuccessful Error.
    """
    if incoming_diagnostics := message_body.get("diagnostics"):
        raise MessageNotSuccessfulError(incoming_diagnostics)

    supplier = message_body.get("supplier")
    fhir_json = message_body.get("fhir_json")
    operation_requested = message_body.get("operation_requested")
    imms_id = message_body.get("imms_id")
    version = message_body.get("version")

    if operation_requested == "CREATE":
        return send_create_request(fhir_json, supplier)

    if operation_requested == "UPDATE":
        return send_update_request(fhir_json, supplier, imms_id, version)

    if operation_requested == "DELETE":
        return send_delete_request(fhir_json, supplier, imms_id)
