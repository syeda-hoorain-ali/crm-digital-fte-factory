"""Standalone Kafka consumer worker using the tested KafkaConsumerService.

This worker runs independently from the API server and processes messages
from Kafka topics, invoking the AI agent and sending responses.
"""

import asyncio
import logging
import signal
import sys

from redis.asyncio import Redis

from ..channels.twilio_client import TwilioClient
from ..channels.gmail_handler import GmailHandler
from ..channels.whatsapp_handler import WhatsAppHandler
from ..config import settings
from ..database.connection import close_engine, init_db
from ..services.kafka_consumer_service import KafkaConsumerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# Global references for cleanup
kafka_consumer_service: KafkaConsumerService | None = None
redis_client: Redis | None = None
shutdown_event = asyncio.Event()


def handle_shutdown_signal(signum, frame) -> None:
    """Handle shutdown signals (SIGTERM, SIGINT)."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


async def main() -> None:
    """Main entry point for the worker."""
    global kafka_consumer_service, redis_client

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    try:
        logger.info("Starting message processor worker...")

        # Step 1: Initialize database
        logger.info("Initializing database connection...")
        await init_db()
        logger.info("Database connection initialized")

        # Step 2: Initialize Redis
        try:
            logger.info("Initializing Redis connection...")
            redis_client = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_client.ping()
            logger.info("Redis connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}", exc_info=True)
            logger.warning("Worker will continue without Redis")

        # Step 3: Initialize Twilio client (for WhatsApp)
        twilio_client = None
        try:
            if settings.twilio_account_sid and settings.twilio_auth_token:
                logger.info("Initializing Twilio client...")
                twilio_client = TwilioClient(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token,
                    whatsapp_from=settings.twilio_app_number
                )
                logger.info("Twilio client initialized")
            else:
                logger.info("Twilio credentials not configured - WhatsApp channel disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}", exc_info=True)
            logger.warning("WhatsApp channel will not be available")

        # Step 4: Initialize WhatsApp handler
        whatsapp_handler = None
        try:
            if twilio_client:
                logger.info("Initializing WhatsApp handler...")
                whatsapp_handler = WhatsAppHandler(
                    twilio_client=twilio_client,
                    auth_token=settings.twilio_auth_token
                )
                
                logger.info("WhatsApp handler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp handler: {e}", exc_info=True)
            logger.warning("WhatsApp channel will not be available")

        # Step 5: Initialize Gmail handler
        gmail_handler = None
        try:
            if settings.gmail_service_account_path:
                from google.oauth2.credentials import Credentials
                import json

                creds_data = json.loads(settings.gmail_service_account_path)
                credentials = Credentials(
                    token=creds_data.get('token'),
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data.get('token_uri'),
                    client_id=creds_data.get('client_id'),
                    client_secret=creds_data.get('client_secret'),
                    scopes=creds_data.get('scopes')
                )

                # Use webhook secret if configured, otherwise use dummy value for dev
                webhook_secret = settings.gmail_webhook_secret or "dev-secret-not-used"
                
                logger.info("Initializing Gmail handler...")
                gmail_handler = GmailHandler(
                    credentials=credentials,
                    webhook_secret=webhook_secret
                )
                logger.info("Initializing Gmail API client...")
                await gmail_handler.initialize()
                logger.info("Gmail handler initialized successfully")
            else:
                logger.info("Gmail credentials path not configured - email channel disabled")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail handler: {e}", exc_info=True)
            logger.warning("Email channel will not be available")

        # Step 6: Initialize and start KafkaConsumerService (tested component)
        logger.info("Initializing Kafka consumer service...")
        kafka_consumer_service = KafkaConsumerService(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="customer-success-agent-group",
            gmail_handler=gmail_handler,
            whatsapp_handler=whatsapp_handler,
        )
        await kafka_consumer_service.start()
        logger.info("Kafka consumer service started successfully")

        logger.info("Message processor worker running...")
        logger.info("Press Ctrl+C to stop")

        # Wait for shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Fatal error in worker: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup
        logger.info("Shutting down message processor worker...")

        # Stop Kafka consumer service
        if kafka_consumer_service:
            try:
                await kafka_consumer_service.stop()
                logger.info("Kafka consumer service stopped")
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer service: {e}")

        # Close Redis connection
        if redis_client:
            try:
                await redis_client.aclose()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")

        # Close database
        await close_engine()
        logger.info("Database connection closed")

        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())