from typing import Literal, Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the MCP server"""

    # File storage settings
    context_dir: str = "context"
    replies_dir: str = "replies"
    tickets_file: str = "context/sample-tickets.json"

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

    @property
    def context_path(self) -> Path:
        """Get absolute path to context directory."""
        return Path(__file__).parent.parent / self.context_dir

    @property
    def replies_path(self) -> Path:
        """Get absolute path to replies directory."""
        return Path(__file__).parent.parent / self.replies_dir

    @property
    def tickets_path(self) -> Path:
        """Get absolute path to tickets file."""
        return Path(__file__).parent.parent / self.tickets_file

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
