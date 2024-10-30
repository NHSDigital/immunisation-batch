import os
import base64
from boto_clients import kms_client


def decrypt_key(os_env_key_name):
      
    # Get the encrypted environment variable
    encrypted_value = os.getenv(os_env_key_name)
    
    # Decrypt the value
    decrypted_response = kms_client.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_value)
    )
    
    # Get the plaintext value
    plaintext_value = decrypted_response['Plaintext'].decode('utf-8')
    
    print(f"Decrypted value of {os_env_key_name}: {plaintext_value}")
    
    return plaintext_value