import json
import os
from fastapi import Request, HTTPException, status
from authlib.integrations.starlette_client import OAuth
from email_agent import config, auth

oauth = OAuth()

def register_oauth_client():
    client_id = None
    client_secret = None
    
    # 1. Try loading from Secret Manager first
    if config.CREDENTIALS_SECRET_ID:
        try:
            creds_data = auth.load_secret_from_secret_manager(config.CREDENTIALS_SECRET_ID)
            web_config = creds_data.get("web", creds_data.get("installed", {}))
            client_id = web_config.get("client_id")
            client_secret = web_config.get("client_secret")
        except Exception as e:
            print(f"Session OAuth Secret Manager Loader Warning: {e}")
            
    # 2. Try loading from local credentials.json
    if not client_id and os.path.exists("credentials.json"):
        try:
            with open("credentials.json", "r") as f:
                creds_data = json.load(f)
                web_config = creds_data.get("web", creds_data.get("installed", {}))
                client_id = web_config.get("client_id")
                client_secret = web_config.get("client_secret")
        except Exception as e:
            print(f"Session OAuth credentials.json Loader Warning: {e}")

    # 3. Fallback to direct environment variables
    if not client_id:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    # Register with Google OIDC Discovery
    oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Register on module import
register_oauth_client()

def get_current_user(request: Request) -> str:
    """
    Reads user info from the encrypted session cookie.
    Validates that the logged-in email is in ALLOWED_EMAILS.
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in via Google."
        )
    
    email = user.get("email", "").strip().lower()
    if email not in config.ALLOWED_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied for email '{email}'. Contact system administrator."
        )
        
    return email
