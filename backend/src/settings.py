from pydantic_settings import BaseSettings
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

    # Database Configuration
    database_url: str = "sqlite:///./crm_agent.db"

    # Application Configuration
    app_name: str = "CloudStream CRM Customer Success AI Agent"
    debug: bool = False

    class Config:
        # env_file = ".env"
        case_sensitive = False


    def configure_llm_provider(self):
        """Configure the global LLM provider for all agents using settings"""

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
