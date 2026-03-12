#!/usr/bin/env python3
"""Script to register Gmail push notifications via Pub/Sub.

This script sets up Gmail watch for incoming emails. The watch expires after 7 days
and must be renewed using the renew_gmail_watch.py script.

Usage:
    python scripts/register_gmail_watch.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from src.channels.gmail_client import GmailClient
from src.config import settings
from src.database.connection import get_session
from src.database.models import GmailWatchState
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def register_gmail_watch():
    """Register Gmail push notifications."""
    try:
        # Load credentials
        logger.info("Loading Gmail credentials...")

        # Option 1: Service account credentials
        if settings.gmail_service_account_path:
            credentials = service_account.Credentials.from_service_account_file(
                settings.gmail_service_account_path,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
        # Option 2: OAuth2 credentials for receiver/support account
        elif settings.gmail_support_credentials_path:
            # Load from saved credentials file
            import json
            with open(settings.gmail_support_credentials_path, 'r') as f:
                creds_data = json.load(f)

            credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )

            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
        # Fallback: Try test credentials (for backward compatibility)
        elif settings.gmail_test_credentials_path:
            logger.warning("Using GMAIL_TEST_CREDENTIALS_PATH - consider using GMAIL_SUPPORT_CREDENTIALS_PATH for receiver account")
            # Load from saved credentials file
            import json
            with open(settings.gmail_test_credentials_path, 'r') as f:
                creds_data = json.load(f)

            credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )

            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
        else:
            logger.error("No Gmail credentials configured")
            sys.exit(1)

        # Initialize Gmail client
        logger.info("Initializing Gmail client...")
        gmail_client = GmailClient(credentials)
        await gmail_client.initialize()

        # Get Pub/Sub topic from settings
        pubsub_topic = getattr(
            settings,
            'gmail_pubsub_topic',
            f'projects/{settings.gcp_project_id}/topics/gmail-notifications' if settings.gcp_project_id else None
        )

        if not pubsub_topic:
            logger.error("GMAIL_PUBSUB_TOPIC not configured in settings")
            sys.exit(1)

        # Register watch
        logger.info(f"Registering Gmail watch with topic: {pubsub_topic}")
        watch_response = await gmail_client.watch_mailbox(
            topic_name=pubsub_topic,
            label_ids=['INBOX']
        )

        # Log success
        history_id = watch_response.get('historyId')
        expiration = watch_response.get('expiration')

        logger.info(
            "Gmail watch registered successfully",
            extra={
                "history_id": history_id,
                "expiration": expiration,
                "topic": pubsub_topic
            }
        )

        # Convert expiration timestamp to readable format
        expiration_dt = None
        if expiration:
            from datetime import datetime, timezone
            expiration_dt = datetime.fromtimestamp(int(expiration) / 1000, tz=timezone.utc)
            logger.info(f"Watch expires at: {expiration_dt.isoformat()}")
            logger.info("Remember to renew the watch before expiration using renew_gmail_watch.py")

        # Get user's email address
        profile = gmail_client.service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        logger.info(f"Gmail account: {email_address}")

        # Store initial history ID in database
        logger.info(f"Storing initial history ID {history_id} for {email_address}")
        async with get_session() as session:
            # Check if state already exists
            result = await session.execute(
                select(GmailWatchState).where(GmailWatchState.email == email_address)
            )
            state = result.scalars().first()

            if state:
                # Update existing state
                state.last_history_id = history_id
                state.watch_expiration = expiration_dt
                state.updated_at = datetime.now(timezone.utc)
                logger.info(f"Updated existing watch state for {email_address}")
            else:
                # Create new state
                state = GmailWatchState(
                    email=email_address,
                    last_history_id=history_id,
                    watch_expiration=expiration_dt
                )
                session.add(state)
                logger.info(f"Created new watch state for {email_address}")

            await session.commit()
            logger.info(f"Successfully stored history ID {history_id} in database")

        return watch_response

    except Exception as e:
        logger.error(f"Failed to register Gmail watch: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    logger.info("Starting Gmail watch registration...")

    try:
        asyncio.run(register_gmail_watch())
        logger.info("Gmail watch registration completed successfully")
    except KeyboardInterrupt:
        logger.info("Registration cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
