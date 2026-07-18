import os

# Google Cloud Platform configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "techsodh")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

# GCS Bucket persistence for token.json
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

# Secret Manager Credentials
CREDENTIALS_SECRET_ID = os.getenv("CREDENTIALS_SECRET_ID")  # Secret Manager Secret ID for credentials.json
TOKEN_SECRET_ID = os.getenv("TOKEN_SECRET_ID")              # Secret Manager Secret ID for token.json

# Security configuration
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "super-secure-token-12345")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Google Sign-In & Session configurations
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "super-secret-session-signing-key-987654321")
ALLOWED_EMAILS = [
    email.strip().lower() 
    for email in os.getenv("ALLOWED_EMAILS", "ronaktalaviya51@gmail.com").split(",") 
    if email.strip()
]

