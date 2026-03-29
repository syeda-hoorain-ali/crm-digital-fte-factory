"""Helper to manually trigger webhooks for E2E testing."""

import base64
import json
import httpx
from typing import Any


class WebhookTrigger:
    """Helper class to manually trigger webhook endpoints for testing."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        """Initialize webhook trigger.

        Args:
            base_url: Base URL of the backend server
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def trigger_gmail_webhook(
        self,
        history_id: str,
        email_address: str = "me",
    ) -> httpx.Response:
        """Trigger Gmail Pub/Sub webhook endpoint.

        Args:
            history_id: Gmail history ID to process
            email_address: Email address (default: "me")

        Returns:
            HTTP response from webhook endpoint
        """
        # Create Pub/Sub notification payload
        notification_data = {
            "emailAddress": email_address,
            "historyId": history_id,
        }

        # Encode as base64 (Pub/Sub format)
        encoded_data = base64.b64encode(
            json.dumps(notification_data).encode("utf-8")
        ).decode("utf-8")

        # Create Pub/Sub message
        pubsub_payload = {
            "message": {
                "data": encoded_data,
                "messageId": f"test-message-{history_id}",
                "publishTime": "2026-03-15T00:00:00.000Z",
                "attributes": {},
            },
            "subscription": "projects/test-project/subscriptions/test-subscription",
        }

        # Send to webhook endpoint
        response = await self.client.post(
            f"{self.base_url}/webhooks/gmail",
            json=pubsub_payload,
            headers={"Content-Type": "application/json"},
        )

        return response

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
