"""Refresh expired Gmail OAuth token."""

import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Load credentials
with open('gmail-support-credentials.json', 'r') as f:
    creds_data = json.load(f)

credentials = Credentials(
    token=creds_data.get('token'),
    refresh_token=creds_data.get('refresh_token'),
    token_uri=creds_data.get('token_uri'),
    client_id=creds_data.get('client_id'),
    client_secret=creds_data.get('client_secret'),
    scopes=creds_data.get('scopes')
)

# Refresh token
print("Refreshing Gmail OAuth token...")
credentials.refresh(Request())
print("Token refreshed successfully!")

# Save updated credentials
updated_creds = {
    'token': credentials.token,
    'refresh_token': credentials.refresh_token,
    'token_uri': credentials.token_uri,
    'client_id': credentials.client_id,
    'client_secret': credentials.client_secret,
    'scopes': credentials.scopes,
    'expiry': credentials.expiry.isoformat() if credentials.expiry else None
}

with open('gmail-support-credentials.json', 'w') as f:
    json.dump(updated_creds, f, indent=2)

print(f"Credentials saved to gmail-support-credentials.json")
print(f"Token expires: {credentials.expiry}")
