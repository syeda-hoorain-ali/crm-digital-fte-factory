"""Generate Gmail API credentials with OAuth token for testing.

This script performs the OAuth flow to generate credentials with access token
that can be used for Gmail E2E testing.

Usage:
    python scripts/generate_gmail_credentials.py --client-secret path/to/client_secret.json --output gmail_test_credentials.json

Requirements:
    - Google Cloud project with Gmail API enabled
    - OAuth 2.0 Client ID (Desktop application) credentials downloaded
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    print("Error: Required packages not installed.")
    print("Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',  # Read, send, delete emails
    'https://www.googleapis.com/auth/gmail.settings.basic'  # Manage basic settings
]


def get_user_email(creds) -> str | None:
    """Get the authenticated user's email address.

    Args:
        creds: Google OAuth credentials

    Returns:
        User's email address
    """
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        return profile['emailAddress']
    except Exception as e:
        print(f"Warning: Could not fetch user email: {e}")
        return None


def update_env_file(variables: dict[str, str]) -> None:
    """Update .env file with Gmail test configuration.

    Args:
        variables: Dictionary of environment variables to add/update
    """
    env_path = Path('.env')

    # Read existing .env content
    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
    else:
        content = ""

    updated_content = content
    added_vars = []

    for var_name, var_value in variables.items():
        pattern = rf'^{var_name}=.*$'
        replacement = f'{var_name}={var_value}'

        if re.search(pattern, content, re.MULTILINE):
            # Update existing variable
            updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
        else:
            # Add new variable
            added_vars.append(f'{var_name}={var_value}')

    # Append new variables if any
    if added_vars:
        # Add section header if this is the first Gmail config
        if 'GMAIL_TEST_CREDENTIALS_PATH' not in content:
            if updated_content and not updated_content.endswith('\n\n'):
                updated_content += '\n\n'
            updated_content += '# Gmail E2E Testing Configuration\n'

        updated_content += '\n'.join(added_vars) + '\n'

    # Write back to .env
    with open(env_path, 'w') as f:
        f.write(updated_content)

    print(f"\n✓ Updated .env file with:")
    for var_name, var_value in variables.items():
        print(f"  {var_name}={var_value}")


def generate_credentials(client_secret_path: str, output_path: str, account_type: str = 'sender') -> None:
    """Generate Gmail credentials with OAuth flow.

    Args:
        client_secret_path: Path to client_secret.json from Google Cloud Console
        output_path: Path to save generated credentials
        account_type: Type of account ('sender' or 'receiver')

    Raises:
        FileNotFoundError: If client_secret_path doesn't exist
        Exception: If OAuth flow fails
    """
    # Verify client secret exists
    if not Path(client_secret_path).exists():
        raise FileNotFoundError(f"Client secret not found: {client_secret_path}")

    # Extract project ID from client_secret.json
    print("Extracting project information...")
    with open(client_secret_path, 'r') as f:
        client_secret_data = json.load(f)

    # Get project_id from client_secret.json
    project_id = None
    if 'installed' in client_secret_data:
        project_id = client_secret_data['installed'].get('project_id')
    elif 'web' in client_secret_data:
        project_id = client_secret_data['web'].get('project_id')

    if project_id:
        print(f"✓ Detected GCP Project ID: {project_id}")

    print("Starting OAuth flow...")
    print(f"Scopes: {', '.join(SCOPES)}")
    print("\nA browser window will open for authentication.")
    print("Please sign in with the Gmail account you want to use for testing.\n")

    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path,
            SCOPES
        )

        # This will open a browser window for authentication
        # Using a specific port range and increased timeout for Windows compatibility
        creds = flow.run_local_server(
            port=0,
            prompt='consent',
            success_message='Authentication successful! You can close this window.',
            open_browser=True,
        )

        print("\n✓ Authentication successful!")

        # Extract credentials data
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(creds_data, f, indent=2)

        print(f"\n✓ Credentials saved to: {output_path}")

        # Get authenticated user's email
        print("\nFetching authenticated user's email...")
        user_email = get_user_email(creds)

        if user_email:
            print(f"✓ Authenticated as: {user_email}")

            # Update .env file based on account type
            print("\nUpdating .env file...")

            if account_type == 'sender':
                # Sender account: only test credentials and email
                variables = {
                    'GMAIL_TEST_CREDENTIALS_PATH': output_path,
                    'GMAIL_TEST_ACCOUNT_EMAIL': user_email
                }
            else:  # receiver
                # Receiver account: support credentials, address, and Pub/Sub config
                variables = {
                    'GMAIL_SUPPORT_CREDENTIALS_PATH': output_path,
                    'GMAIL_SUPPORT_ADDRESS': user_email
                }
                if project_id:
                    variables['GCP_PROJECT_ID'] = project_id
                    variables['GMAIL_PUBSUB_TOPIC'] = f'projects/{project_id}/topics/gmail-notifications'

            update_env_file(variables)
        else:
            print("\n⚠ Could not fetch user email. Please manually add to .env:")
            if account_type == 'sender':
                print(f"   GMAIL_TEST_CREDENTIALS_PATH={output_path}")
                print(f"   GMAIL_TEST_ACCOUNT_EMAIL=<your-email@gmail.com>")
            else:  # receiver
                print(f"   GMAIL_SUPPORT_CREDENTIALS_PATH={output_path}")
                print(f"   GMAIL_SUPPORT_ADDRESS=<your-email@gmail.com>")
                if project_id:
                    print(f"   GCP_PROJECT_ID={project_id}")
                    print(f"   GMAIL_PUBSUB_TOPIC=projects/{project_id}/topics/gmail-notifications")

        # Next steps based on account type
        print("\nNext steps:")
        if account_type == 'sender':
            print(f"1. ✓ Sender account credentials configured in .env")
            print(f"2. Set up receiver account (see tests/e2e/README_GMAIL_E2E.md)")
            print(f"3. Run E2E tests: uv run pytest tests/e2e/test_gmail_real_flow.py -v -s")
        else:  # receiver
            print(f"1. ✓ Receiver account credentials configured in .env")
            if project_id:
                print(f"2. Create Pub/Sub topic in Google Cloud Console:")
                print(f"   - Project: {project_id}")
                print(f"   - Topic: gmail-notifications")
                print(f"   - Grant permission to: gmail-api-push@system.gserviceaccount.com")
            else:
                print(f"2. Set up Gmail Pub/Sub (see tests/e2e/README_GMAIL_E2E.md)")
            print(f"3. Set up local tunnel (VS Code port forwarding or ngrok)")
            print(f"4. Create Pub/Sub push subscription with webhook URL")
            print(f"5. Run: uv run scripts/register_gmail_watch.py")
            print(f"6. Set up sender account and run E2E tests")

    except Exception as e:
        print(f"\n✗ Error during OAuth flow: {e}")
        raise


def verify_credentials(credentials_path: str) -> None:
    """Verify that credentials are valid and can be refreshed.

    Args:
        credentials_path: Path to credentials JSON file

    Raises:
        FileNotFoundError: If credentials file doesn't exist
        Exception: If credentials are invalid
    """
    if not Path(credentials_path).exists():
        raise FileNotFoundError(f"Credentials not found: {credentials_path}")

    print(f"Verifying credentials: {credentials_path}")

    try:
        with open(credentials_path, 'r') as f:
            creds_data = json.load(f)

        # Check required fields
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if field not in creds_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        print("✓ Credentials file structure is valid")

        # Try to create Credentials object
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data.get('scopes', SCOPES)
        )

        # Try to refresh if expired
        if creds.expired and creds.refresh_token:
            print("Token expired, attempting refresh...")
            creds.refresh(Request())
            print("✓ Token refreshed successfully")

            # Update file with new token
            creds_data['token'] = creds.token
            with open(credentials_path, 'w') as f:
                json.dump(creds_data, f, indent=2)
            print(f"✓ Updated credentials saved to: {credentials_path}")
        else:
            print("✓ Token is valid")

        print("\n✓ Credentials are valid and ready to use!")

    except Exception as e:
        print(f"\n✗ Credentials verification failed: {e}")
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate or verify Gmail API credentials for E2E testing'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate new credentials')
    generate_parser.add_argument(
        '--client-secret',
        required=True,
        help='Path to client_secret.json from Google Cloud Console'
    )
    generate_parser.add_argument(
        '--output',
        default='gmail_test_credentials.json',
        help='Output path for generated credentials (default: gmail_test_credentials.json)'
    )
    generate_parser.add_argument(
        '--account-type',
        choices=['sender', 'receiver'],
        default='sender',
        help='Type of account: sender (test account) or receiver (support account). Default: sender'
    )

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify existing credentials')
    verify_parser.add_argument(
        '--credentials',
        required=True,
        help='Path to credentials JSON file to verify'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'generate':
            generate_credentials(args.client_secret, args.output, args.account_type)
        elif args.command == 'verify':
            verify_credentials(args.credentials)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()