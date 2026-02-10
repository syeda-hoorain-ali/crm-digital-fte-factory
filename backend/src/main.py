import asyncio
from src.channels.channel_handler import run_channel_demo
from src.agent import run_customer_success_demo
from src.settings import get_settings


settings = get_settings()

def main():
    print("Starting CloudStream CRM Customer Success AI Agent - Incubation Stage")
    settings.configure_llm_provider()

    # Run the customer success demo
    asyncio.run(run_customer_success_demo())

    # Run the channel handler demo
    asyncio.run(run_channel_demo())


if __name__ == "__main__":
    main()
