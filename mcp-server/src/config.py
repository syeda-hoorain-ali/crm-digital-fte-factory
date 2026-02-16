from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the MCP server"""

    # Database settings
    database_url: str = "sqlite:///./mcp_server.db"

    # Authentication settings
    mcp_server_token: Optional[str] = None

    # Server settings
    server_port: int = 8080
    server_host: str = "0.0.0.0"

    # Rate limiting settings
    rate_limit_requests: int = 100  # Number of requests allowed
    rate_limit_window: int = 60     # Time window in seconds

    # Environment
    environment: str = "development" # development, production, testing
    debug: bool = False
    log_level: str = "INFO"  # Default value

    def model_post_init(self, __context):
        """Post-initialization hook to customize settings based on environment"""
        if self.environment == "testing":
            self.database_url = "sqlite:///./test.db"
        elif self.environment == "production":
            # In production, check if using SQLite and raise an error
            if self.database_url.startswith("sqlite://"):
                raise ValueError("SQLite database is not allowed in production environment. Please use a production-ready database like PostgreSQL.")

        # Set appropriate logging level based on debug and environment
        if self.debug:
            self.log_level = "DEBUG"
        elif self.environment == "production":
            self.log_level = "ERROR"
        else:
            self.log_level = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
