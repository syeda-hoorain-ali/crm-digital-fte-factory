from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from openai import AsyncOpenAI
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LLM Configuration
    gemini_api_key: str
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-2.5-flash"

    # Database Configuration
    database_url: str = ""  # Default will be set in model_post_init based on environment

    # MCP Server Configuration
    mcp_server_url: str = "http://localhost:8080"
    mcp_server_token: str = ""

    # Application Configuration
    app_name: str = "CloudStream CRM Customer Success AI Agent"
    debug: bool = False
    environment: str = "development"  # development, production, testing

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )

    def model_post_init(self, _context):
        """Configure application settings based on environment"""

        # Handle database configuration based on environment
        if self.environment == "testing":
            # In testing mode, always use SQLite
            self.database_url = "sqlite:///./test_backend.db"
        elif self.environment == "production":
            # In production, require database_url to be set and must not be SQLite
            if not self.database_url:
                raise ValueError("database_url environment variable is required in production mode")
            if self.database_url.startswith("sqlite://"):
                raise ValueError("SQLite database is not allowed in production environment. Please use a production-ready database like PostgreSQL.")
        elif self.environment == "development":
            # In development mode:
            # - If user has set database_url, use it (SQLAlchemy session)
            # - If user hasn't set database_url, use SQLite
            if not self.database_url:
                self.database_url = "sqlite:///./crm_agent_dev.db"
            # If database_url is provided, we use it as-is (assuming SQLAlchemy-compatible URL)

        # Configure the global LLM provider for all agents using settings
        set_tracing_disabled(True)
        set_default_openai_api("chat_completions")

        external_client = AsyncOpenAI(
            api_key=self.gemini_api_key,
            base_url=self.gemini_base_url,
        )

        set_default_openai_client(external_client)

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid reloading from .env on every call"""
    return Settings()
