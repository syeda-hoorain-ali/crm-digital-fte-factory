"""Channel-specific response formatters for multi-channel support."""

from typing import Protocol


class ResponseFormatter(Protocol):
    """Protocol for channel-specific response formatters."""

    def format(self, content: str, metadata: dict | None = None) -> str:
        """Format response content for specific channel.

        Args:
            content: Raw response content
            metadata: Optional metadata for formatting (e.g., customer name, links)

        Returns:
            Formatted response string
        """
        ...


class EmailFormatter:
    """Gmail/Email response formatter with professional structure."""

    def format(self, content: str, metadata: dict | None = None) -> str:
        """Format response for email with greeting, body, and signature.

        Args:
            content: Raw response content
            metadata: Optional metadata (customer_name, subject, etc.)

        Returns:
            Formatted email response
        """
        metadata = metadata or {}
        customer_name = metadata.get("customer_name", "Valued Customer")

        # Build email structure
        response = f"Dear {customer_name},\n\n"
        response += content
        response += "\n\n"
        response += "Best regards,\n"
        response += "CloudStream CRM Support Team\n"
        response += "support@cloudstream.com\n"
        response += "Available 24/7 for your assistance"

        return response


class WhatsAppFormatter:
    """WhatsApp response formatter with concise, conversational style."""

    def format(self, content: str, metadata: dict | None = None) -> str:
        """Format response for WhatsApp with emoji and brevity.

        Args:
            content: Raw response content
            metadata: Optional metadata

        Returns:
            Formatted WhatsApp response
        """
        # WhatsApp prefers shorter, more conversational messages
        # Add friendly emoji and keep it concise
        response = f"👋 {content}"

        # Add helpful closing
        response += "\n\nNeed more help? Just reply here! 💬"

        return response


class WebFormFormatter:
    """Web form response formatter with structured HTML-friendly content."""

    def format(self, content: str, metadata: dict | None = None) -> str:
        """Format response for web form with clear structure.

        Args:
            content: Raw response content
            metadata: Optional metadata

        Returns:
            Formatted web form response
        """
        metadata = metadata or {}

        # Web forms can handle more structured content
        response = "**CloudStream CRM Support**\n\n"
        response += content
        response += "\n\n---\n"
        response += "**Need additional assistance?**\n"
        response += "- Reply to this message\n"
        response += "- Visit our Help Center: https://help.cloudstream.com\n"
        response += "- Call us: 1-800-CLOUD-CRM"

        return response


class APIFormatter:
    """API response formatter with minimal formatting (raw content)."""

    def format(self, content: str, metadata: dict | None = None) -> str:
        """Format response for API with minimal changes.

        Args:
            content: Raw response content
            metadata: Optional metadata

        Returns:
            Formatted API response (mostly unchanged)
        """
        # API consumers typically want raw content without extra formatting
        # They'll handle their own presentation layer
        return content


# Formatter registry for easy lookup
FORMATTERS = {
    "email": EmailFormatter(),
    "whatsapp": WhatsAppFormatter(),
    "web_form": WebFormFormatter(),
    "api": APIFormatter(),
}


def format_response(content: str, channel: str, metadata: dict | None = None) -> str:
    """Format response content for specific channel.

    Args:
        content: Raw response content
        channel: Channel name (email, whatsapp, web_form, api)
        metadata: Optional metadata for formatting

    Returns:
        Formatted response string

    Raises:
        ValueError: If channel is not supported
    """
    channel_lower = channel.lower()

    if channel_lower not in FORMATTERS:
        raise ValueError(
            f"Unsupported channel: {channel}. "
            f"Supported channels: {', '.join(FORMATTERS.keys())}"
        )

    formatter = FORMATTERS[channel_lower]
    return formatter.format(content, metadata)
