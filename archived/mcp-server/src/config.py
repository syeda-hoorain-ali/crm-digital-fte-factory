from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the MCP server"""

    # Database settings
    database_url: str

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
    log_level: Literal['DEBUG', 'INFO', 'ERROR'] = "INFO"  # Default value

    def model_post_init(self, __context):
        """Post-initialization hook to customize settings based on environment"""
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
