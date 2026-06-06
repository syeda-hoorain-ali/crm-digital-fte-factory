"""Standalone Kafka consumer worker using the tested KafkaConsumerService.

This worker runs independently from the API server and processes messages
from Kafka topics, invoking the AI agent and sending responses.
"""

import asyncio
import logging
import signal
import sys
from aiohttp import web
from prometheus_client import make_asgi_app

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
metrics_server_task: asyncio.Task | None = None


def handle_shutdown_signal(signum, frame) -> None:
    """Handle shutdown signals (SIGTERM, SIGINT)."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


async def start_metrics_server() -> None:
    """Start HTTP server for Prometheus metrics on port 8080."""
    try:
        # Create aiohttp app with Prometheus metrics endpoint
        app = web.Application()

        # Mount Prometheus metrics at /metrics
        metrics_app = make_asgi_app()

        async def metrics_handler(request):
            """Handle metrics requests."""
            scope = {
                'type': 'http',
                'method': request.method,
                'path': request.path,
                'query_string': request.query_string.encode(),
                'headers': [(k.encode(), v.encode()) for k, v in request.headers.items()],
            }

            async def receive():
                return {'type': 'http.request', 'body': await request.read()}

            response_started = False
            status = 200
            headers = []
            body_parts = []

            async def send(message):
                nonlocal response_started, status, headers, body_parts
                if message['type'] == 'http.response.start':
                    response_started = True
                    status = message['status']
                    headers = message.get('headers', [])
                elif message['type'] == 'http.response.body':
                    body_parts.append(message.get('body', b''))

            await metrics_app(scope, receive, send)

            response = web.Response(
                status=status,
                headers={k.decode(): v.decode() for k, v in headers},
                body=b''.join(body_parts)
            )
            return response

        app.router.add_get('/metrics', metrics_handler)

        # Add health check endpoint
        async def health_handler(request):
            return web.Response(text='OK', status=200)

        app.router.add_get('/health', health_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()

        logger.info("Metrics HTTP server started on port 8080")

        # Keep server running until shutdown
        await shutdown_event.wait()

        # Cleanup
        await runner.cleanup()
        logger.info("Metrics HTTP server stopped")

    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}", exc_info=True)


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
            # Check for credentials (support/receiver account for webhook processing)
            credentials_path = None
            if settings.gmail_support_credentials_path:
                credentials_path = settings.gmail_support_credentials_path
                logger.info(f"Using support/receiver account credentials: {credentials_path}")
            elif settings.gmail_service_account_path:
                credentials_path = settings.gmail_service_account_path
                logger.info(f"Using service account: {credentials_path}")
            elif settings.gmail_test_credentials_path:
                credentials_path = settings.gmail_test_credentials_path
                logger.info(f"Using test credentials: {credentials_path}")

            if credentials_path:
                from google.oauth2.credentials import Credentials
                import json
                import os

                # Resolve relative path
                if not os.path.isabs(credentials_path):
                    credentials_path = os.path.join(os.getcwd(), credentials_path)
                    logger.info(f"Resolved path: {credentials_path}")

                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"Gmail credentials not found at {credentials_path}")

                logger.info(f"Loading credentials from {credentials_path}")
                with open(credentials_path, 'r') as f:
                    creds_data = json.load(f)

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

        # Step 6: Start metrics HTTP server in background
        global metrics_server_task
        logger.info("Starting metrics HTTP server...")
        metrics_server_task = asyncio.create_task(start_metrics_server())

        # Step 7: Initialize and start KafkaConsumerService (tested component)
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