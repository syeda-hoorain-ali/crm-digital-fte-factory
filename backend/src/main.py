"""FastAPI application for Customer Success Agent API."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from sqlalchemy import text
from redis.asyncio import Redis

from .config import settings
from .api.routes.agent import router as agent_router
from .api.webhooks import web_form, whatsapp, gmail
from .api import customers
from .database.connection import init_db, close_engine, get_session
from .channels.twilio_client import TwilioClient
from .channels.whatsapp_handler import WhatsAppHandler
from .channels.gmail_handler import GmailHandler
from .kafka.producer import KafkaMessageProducer
from .utils.rate_limiter import RateLimiter
from .middleware.correlation_id import CorrelationIdMiddleware, configure_structured_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events:
    - Startup: Validate configuration and initialize database connection
    - Shutdown: Cleanup database connections
    """
    # Startup
    logger.info("Starting up...")

    # Step 1: Validate configuration on startup
    try:
        logger.info("Validating configuration...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Log Level: {settings.log_level}")
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise RuntimeError(
            f"Configuration validation failed. Please check your .env file and environment variables: {e}"
        ) from e

    # Step 2: Initialize database connection
    try:
        logger.info("Initializing database connection...")
        await init_db()
        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise RuntimeError(
            f"Database initialization failed. Please check your DATABASE_URL: {e}"
        ) from e

    # Step 3: Initialize Kafka producer and create topics
    kafka_producer_instance = None
    try:
        logger.info("Initializing Kafka producer...")
        kafka_producer_instance = KafkaMessageProducer(settings.kafka_bootstrap_servers)
        await kafka_producer_instance.start()
        logger.info("Kafka producer initialized successfully")

        # Create Kafka topics if they don't exist
        try:
            from aiokafka.admin import AIOKafkaAdminClient, NewTopic

            logger.info("Checking/creating Kafka topics...")
            admin_client = AIOKafkaAdminClient(
                bootstrap_servers=settings.kafka_bootstrap_servers
            )
            await admin_client.start()

            try:
                # Define required topics
                required_topics = [
                    NewTopic(name='customer-intake.all.inbound', num_partitions=3, replication_factor=1),
                    NewTopic(name='customer-intake.email.inbound', num_partitions=3, replication_factor=1),
                    NewTopic(name='customer-intake.webform.inbound', num_partitions=3, replication_factor=1),
                    NewTopic(name='customer-intake.whatsapp.inbound', num_partitions=3, replication_factor=1),
                ]

                # Get existing topics
                existing_topics = await admin_client.list_topics()

                # Filter out topics that already exist
                topics_to_create = [
                    topic for topic in required_topics
                    if topic.name not in existing_topics
                ]

                if topics_to_create:
                    logger.info(f"Creating {len(topics_to_create)} Kafka topics...")
                    await admin_client.create_topics(topics_to_create, validate_only=False)
                    logger.info(f"Created topics: {[t.name for t in topics_to_create]}")
                else:
                    logger.info("All required Kafka topics already exist")

            finally:
                await admin_client.close()

        except Exception as topic_error:
            logger.warning(f"Failed to create Kafka topics: {topic_error}")
            logger.warning("Topics may need to be created manually or by infrastructure")

    except Exception as e:
        logger.warning(f"Failed to initialize Kafka producer: {e}")
        logger.warning("Continuing without Kafka - messages will not be routed")

    # Step 4: Initialize Redis and rate limiter
    redis_client = None
    rate_limiter_instance = None
    try:
        logger.info("Initializing Redis connection...")
        redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
        await redis_client.ping()
        rate_limiter_instance = RateLimiter(redis_client, rate_limit=10, window_seconds=60)
        logger.info("Redis and rate limiter initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis: {e}")
        logger.warning("Continuing without rate limiting")

    # Step 5: Initialize Twilio client and WhatsApp handler
    twilio_client_instance = None
    whatsapp_handler_instance = None
    try:
        logger.info("Initializing Twilio client...")
        twilio_client_instance = TwilioClient(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            whatsapp_from=settings.twilio_app_number
        )
        whatsapp_handler_instance = WhatsAppHandler(
            twilio_client=twilio_client_instance,
            auth_token=settings.twilio_auth_token
        )
        logger.info("Twilio client and WhatsApp handler initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Twilio/WhatsApp: {e}")
        logger.warning("WhatsApp channel will not be available")

    # Step 6: Initialize Gmail handler
    gmail_handler_instance = None
    try:
        # Check for credentials (support/receiver account for webhook processing)
        credentials_path = None
        if settings.gmail_support_credentials_path:
            credentials_path = settings.gmail_support_credentials_path
            print(f"[GMAIL] Using support/receiver account credentials: {credentials_path}")
        elif settings.gmail_service_account_path:
            credentials_path = settings.gmail_service_account_path
            print(f"[GMAIL] Using service account: {credentials_path}")
        elif settings.gmail_test_credentials_path:
            # Fallback for backward compatibility (but should use gmail_support_credentials_path)
            credentials_path = settings.gmail_test_credentials_path
            print(f"[GMAIL] ⚠️  Using test credentials (consider using GMAIL_SUPPORT_CREDENTIALS_PATH): {credentials_path}")

        if credentials_path:
            print("[GMAIL] Initializing Gmail handler...")
            from google.oauth2.credentials import Credentials
            import json
            import os

            # Resolve relative path
            if not os.path.isabs(credentials_path):
                credentials_path = os.path.join(os.getcwd(), credentials_path)
                print(f"[GMAIL] Resolved path: {credentials_path}")

            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Gmail credentials not found at {credentials_path}")

            print(f"[GMAIL] Loading credentials from {credentials_path}")
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

            print("[GMAIL] Creating Gmail handler instance...")
            gmail_handler_instance = GmailHandler(
                credentials=credentials,
                webhook_secret=webhook_secret
            )
            print("[GMAIL] Initializing Gmail API client...")
            await gmail_handler_instance.initialize()
            print("[GMAIL] Gmail handler initialized successfully")
            logger.info("Gmail handler initialized successfully")
        else:
            print("[GMAIL] No credentials configured - email channel disabled")
            logger.info("Gmail credentials not configured - email channel disabled")
    except Exception as e:
        print(f"[GMAIL] Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Failed to initialize Gmail handler: {e}", exc_info=True)
        logger.warning("Email channel will not be available")

    # Wire up handlers to webhook modules
    if kafka_producer_instance:
        web_form.kafka_producer = kafka_producer_instance
        whatsapp.kafka_producer = kafka_producer_instance
        gmail.kafka_producer = kafka_producer_instance

    if rate_limiter_instance:
        web_form.rate_limiter = rate_limiter_instance
        whatsapp.rate_limiter = rate_limiter_instance
        gmail.rate_limiter = rate_limiter_instance

    if twilio_client_instance:
        whatsapp.twilio_client = twilio_client_instance

    if whatsapp_handler_instance:
        whatsapp.whatsapp_handler = whatsapp_handler_instance

    if gmail_handler_instance:
        gmail.gmail_handler = gmail_handler_instance

    # Store instances in app.state for health check access
    app.state.kafka_producer = kafka_producer_instance
    app.state.redis_client = redis_client

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop Kafka producer
    if kafka_producer_instance:
        try:
            await kafka_producer_instance.stop()
            logger.info("Kafka producer stopped")
        except Exception as e:
            logger.error(f"Error stopping Kafka producer: {e}")

    # Close Redis connection
    if redis_client:
        try:
            await redis_client.aclose()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

    # Close database
    await close_engine()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Customer Success Agent API",
    description="Production-ready customer support agent with OpenAI Agents SDK and multi-channel intake",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure structured logging
configure_structured_logging()

# Add correlation ID middleware (before CORS)
app.add_middleware(CorrelationIdMiddleware)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(agent_router)
app.include_router(web_form.router, prefix="/support", tags=["support"])
app.include_router(whatsapp.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(gmail.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(customers.router, prefix="/api", tags=["customers"])

@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Verifies connectivity to:
    - Database (PostgreSQL)
    - Redis (rate limiting)
    - Kafka (message routing)

    Returns:
        dict: Health status with component details

    Raises:
        HTTPException: 503 status if any critical component is unhealthy
    """
    from .monitoring.prometheus_metrics import update_health_status

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }

    all_healthy = True

    # Check database
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Connected"
        }
        update_health_status("database", True)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        update_health_status("database", False)
        all_healthy = False

    # Check Redis
    try:
        if hasattr(app.state, 'redis_client') and app.state.redis_client:
            # Redis client is initialized in lifespan
            await app.state.redis_client.ping()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Connected"
            }
            update_health_status("redis", True)
        else:
            health_status["components"]["redis"] = {
                "status": "unknown",
                "message": "Not initialized"
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        update_health_status("redis", False)
        all_healthy = False

    # Check Kafka
    try:
        if hasattr(app.state, 'kafka_producer') and app.state.kafka_producer:
            # Kafka producer is initialized in lifespan
            health_status["components"]["kafka"] = {
                "status": "healthy",
                "message": "Producer initialized"
            }
            update_health_status("kafka", True)
        else:
            health_status["components"]["kafka"] = {
                "status": "degraded",
                "message": "Producer not initialized"
            }
            update_health_status("kafka", False)
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        health_status["components"]["kafka"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        update_health_status("kafka", False)
        all_healthy = False

    # Set overall status
    if not all_healthy:
        health_status["status"] = "unhealthy"
        raise HTTPException(
            status_code=503,
            detail=health_status
        )

    return health_status

