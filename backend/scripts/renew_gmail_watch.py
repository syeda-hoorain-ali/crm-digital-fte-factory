#!/usr/bin/env python3
"""Script to renew Gmail push notifications.

Gmail watch expires after 7 days. This script should be run as a cron job
to automatically renew the watch before expiration.

Recommended cron schedule (run every 6 days):
    0 0 */6 * * /path/to/python /path/to/renew_gmail_watch.py

Usage:
    python scripts/renew_gmail_watch.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from src.channels.gmail_client import GmailClient
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def renew_gmail_watch():
    """Renew Gmail push notifications.

    This stops the existing watch and creates a new one.
    """
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

        # Stop existing watch (if any)
        logger.info("Stopping existing Gmail watch...")
        try:
            await gmail_client.stop_watch()
            logger.info("Existing watch stopped successfully")
        except Exception as e:
            logger.warning(f"Failed to stop existing watch (may not exist): {e}")

        # Get Pub/Sub topic from settings
        pubsub_topic = getattr(
            settings,
            'gmail_pubsub_topic',
            f'projects/{settings.gcp_project_id}/topics/gmail-notifications' if settings.gcp_project_id else None
        )

        if not pubsub_topic:
            logger.error("GMAIL_PUBSUB_TOPIC not configured in settings")
            sys.exit(1)

        # Register new watch
        logger.info(f"Registering new Gmail watch with topic: {pubsub_topic}")
        watch_response = await gmail_client.watch_mailbox(
            topic_name=pubsub_topic,
            label_ids=['INBOX']
        )

        # Log success
        history_id = watch_response.get('historyId')
        expiration = watch_response.get('expiration')

        logger.info(
            "Gmail watch renewed successfully",
            extra={
                "history_id": history_id,
                "expiration": expiration,
                "topic": pubsub_topic
            }
        )

        # Convert expiration timestamp to readable format
        if expiration:
            expiration_dt = datetime.fromtimestamp(int(expiration) / 1000)
            logger.info(f"New watch expires at: {expiration_dt.isoformat()}")

            # Calculate next renewal date (6 days from now)
            next_renewal = datetime.now() + timedelta(days=6)
            logger.info(f"Next renewal recommended at: {next_renewal.isoformat()}")

        return watch_response

    except Exception as e:
        logger.error(f"Failed to renew Gmail watch: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    logger.info("Starting Gmail watch renewal...")

    try:
        asyncio.run(renew_gmail_watch())
        logger.info("Gmail watch renewal completed successfully")
    except KeyboardInterrupt:
        logger.info("Renewal cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Renewal failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
