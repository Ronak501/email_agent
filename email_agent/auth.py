import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import storage
from google.cloud import secretmanager
from email_agent import config

def load_secret_from_secret_manager(secret_id: str) -> dict:
    """Helper to fetch a JSON secret payload from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(name=secret_id)
    return json.loads(response.payload.data.decode("UTF-8"))

def write_secret_to_secret_manager(secret_id: str, payload: dict):
    """Helper to write/update a JSON secret version in Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    # Parse parent secret name from versioned secret ID
    # e.g., 'projects/techsodh/secrets/token/versions/latest' -> 'projects/techsodh/secrets/token'
    parts = secret_id.split('/')
    parent = "/".join(parts[:4])
    
    payload_bytes = json.dumps(payload).encode("UTF-8")
    client.add_secret_version(
        parent=parent,
        payload={"data": payload_bytes}
    )

def get_gmail_service():
    """
    Authenticates the user and returns the Gmail API service resource.
    Supports GCS and Secret Manager persistence for token.json and Secret Manager for credentials.json.
    """
    creds = None
    token_path = 'token.json'
    
    # 1. Retrieve token.json (from Secret Manager, GCS, or Local file)
    if config.TOKEN_SECRET_ID:
        try:
            token_payload = load_secret_from_secret_manager(config.TOKEN_SECRET_ID)
            with open(token_path, 'w') as f:
                json.dump(token_payload, f)
            print("Loaded token.json from Secret Manager.")
        except Exception as e:
            print(f"Secret Manager Token Retrieval Warning: {e}")
            
    elif config.GCS_BUCKET_NAME:
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(config.GCS_BUCKET_NAME)
            blob = bucket.blob('token.json')
            if blob.exists():
                blob.download_to_filename(token_path)
                print(f"Loaded token.json from GCS bucket: {config.GCS_BUCKET_NAME}")
        except Exception as e:
            print(f"GCS Token Retrieval Warning: {e}")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, config.GMAIL_SCOPES)
    
    # 2. Refresh or trigger OAuth if creds are invalid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if config.CREDENTIALS_SECRET_ID:
                client_config = load_secret_from_secret_manager(config.CREDENTIALS_SECRET_ID)
                flow = InstalledAppFlow.from_client_config(client_config, config.GMAIL_SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', config.GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save token locally
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
        # Sync back token to Cloud storage
        if config.TOKEN_SECRET_ID:
            try:
                write_secret_to_secret_manager(config.TOKEN_SECRET_ID, json.loads(creds.to_json()))
                print("Uploaded updated token.json to Secret Manager.")
            except Exception as e:
                print(f"Secret Manager Token Upload Warning: {e}")
                
        if config.GCS_BUCKET_NAME:
            try:
                storage_client = storage.Client()
                bucket = storage_client.bucket(config.GCS_BUCKET_NAME)
                blob = bucket.blob('token.json')
                blob.upload_from_filename(token_path)
                print("Uploaded updated token.json to GCS bucket.")
            except Exception as e:
                print(f"GCS Token Upload Warning: {e}")

    return build('gmail', 'v1', credentials=creds)
