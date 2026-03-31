"""
Configuration management using Pydantic Settings.

This module provides type-safe configuration loading from environment variables
and .env files with validation on startup.
"""

from dotenv import load_dotenv, find_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import AsyncOpenAI
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled


load_dotenv(find_dotenv())

class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string (required)",
        examples=["postgresql://user:password@localhost:5432/dbname"]
    )

    # Gemini
    gemini_api_key: str = Field(
        ...,
        description="Gemini API key for agent operations (required)"
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="Gemini base URL for agent operations"
    )

    # Embedding Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Model name for text embeddings"
    )
    embedding_dimension: int = Field(
        default=384,
        description="Dimension of embedding vectors",
        ge=1
    )

    # Application
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port",
        ge=1,
        le=65535
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    # Agent Configuration
    agent_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model for agent operations"
    )
    agent_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for agent responses",
        ge=1
    )
    agent_temperature: float = Field(
        default=0.7,
        description="Agent temperature for response generation",
        ge=0.0,
        le=2.0
    )
    agent_cost_per_million_tokens: float = Field(
        default=6.25,
        description="Cost per million tokens in USD for agent model",
        ge=0.0
    )

    # Escalation Configuration
    escalation_email_low: str = Field(
        default="support-tier1@cloudstream.com",
        description="Email for low priority escalations"
    )
    escalation_email_medium: str = Field(
        default="support-tier2@cloudstream.com",
        description="Email for medium priority escalations"
    )
    escalation_email_high: str = Field(
        default="support-senior@cloudstream.com",
        description="Email for high priority escalations"
    )
    escalation_email_critical: str = Field(
        default="support-vip@cloudstream.com",
        description="Email for critical priority escalations"
    )

    # Email Notification Configuration
    smtp_host: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname"
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
        ge=1,
        le=65535
    )
    smtp_username: str = Field(
        default="",
        description="SMTP authentication username"
    )
    smtp_password: str = Field(
        default="",
        description="SMTP authentication password"
    )
    smtp_from_email: str = Field(
        default="support@cloudstream.com",
        description="Sender email address for notifications"
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Use TLS encryption for SMTP"
    )
    enable_email_notifications: bool = Field(
        default=False,
        description="Enable email notifications (requires SMTP configuration)"
    )

    # Database Connection Pool
    db_pool_size: int = Field(
        default=10,
        description="Maximum number of database connections in the pool",
        ge=1
    )
    db_max_overflow: int = Field(
        default=20,
        description="Maximum overflow connections beyond pool_size",
        ge=0
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=1
    )

    # Knowledge Base Configuration
    kb_search_limit: int = Field(
        default=5,
        description="Number of knowledge base results to return",
        ge=1
    )
    kb_min_similarity: float = Field(
        default=0.7,
        description="Minimum similarity score for knowledge base results",
        ge=0.0,
        le=1.0
    )

    # Twilio Configuration
    twilio_account_sid: str = Field(
        default="",
        description="Twilio account SID (required for WhatsApp)"
    )
    twilio_auth_token: str = Field(
        default="",
        description="Twilio auth token (required for WhatsApp)"
    )
    twilio_whatsapp_from: str = Field(
        default="",
        description="Twilio WhatsApp sender number (format: whatsapp:+1234567890)"
    )

    # Gmail Configuration
    gmail_test_account_email: str = Field(
        default="",
        description="Gmail test account email address (for E2E testing - sender account)"
    )
    gmail_test_credentials_path: str = Field(
        default="",
        description="Path to Gmail API OAuth credentials JSON file (for E2E testing - sender account)"
    )
    gmail_support_credentials_path: str = Field(
        default="",
        description="Path to Gmail API OAuth credentials JSON file (for receiver/support account)"
    )
    gmail_service_account_path: str = Field(
        default="",
        description="Path to Gmail API service account credentials JSON file (for production)"
    )
    gmail_support_address: str = Field(
        default="",
        description="Gmail address that receives customer emails (receiver/support account)"
    )
    gmail_pubsub_topic: str = Field(
        default="",
        description="Google Cloud Pub/Sub topic for Gmail notifications (format: projects/PROJECT_ID/topics/TOPIC_NAME)"
    )
    gmail_webhook_secret: str = Field(
        default="",
        description="Secret for validating Gmail webhook requests"
    )
    gcp_project_id: str = Field(
        default="",
        description="Google Cloud Platform project ID"
    )

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for rate limiting"
    )

    # Observability Configuration
    enable_debug_logging: bool = Field(
        default=False,
        description="Enable detailed request/response logging"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable performance metrics collection"
    )
    enable_tracing: bool = Field(
        default=False,
        description="Enable distributed tracing"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that database_url is not empty and starts with postgresql."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql://' or 'postgresql+asyncpg://'"
            )
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Remove sslmode and channel_binding parameters (asyncpg doesn't support them)
        # asyncpg uses SSL by default for Neon connections
        if "?" in v:
            base_url, params = v.split("?", 1)
            # Filter out incompatible parameters
            param_pairs = [p for p in params.split("&") if not p.startswith(("sslmode=", "channel_binding="))]
            if param_pairs:
                v = f"{base_url}?{'&'.join(param_pairs)}"
            else:
                v = base_url

        return v

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_api_key(cls, v: str) -> str:
        """Validate that gemini_api_key is not empty."""
        if not v:
            raise ValueError("GEMINI_API_KEY cannot be empty")
        if not v.startswith("AI"):
            raise ValueError("GEMINI_API_KEY must start with 'AI'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log_level is a valid logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{v}'"
            )
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate that environment is a known value."""
        valid_envs = {"development", "staging", "production", "test"}
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(
                f"ENVIRONMENT must be one of {valid_envs}, got '{v}'"
            )
        return v_lower
    
    def model_post_init(self, _context):
        """Configure the global LLM provider for all agents"""
        set_tracing_disabled(True)
        set_default_openai_api("chat_completions")

        external_client = AsyncOpenAI(
            api_key=self.gemini_api_key,
            base_url=self.gemini_base_url,
        )

        set_default_openai_client(external_client)

# Singleton instance - will be initialized on first import
# This will raise validation errors if required fields are missing
settings = Settings()
