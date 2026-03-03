"""Unit tests for channel-specific response formatters."""

import pytest

from src.agent.formatters import (
    EmailFormatter,
    WhatsAppFormatter,
    WebFormFormatter,
    APIFormatter,
    format_response,
    FORMATTERS,
)


# ============================================================================
# Tests for EmailFormatter (T083)
# ============================================================================

@pytest.mark.unit
@pytest.mark.formatters
class TestEmailFormatter:
    """Unit tests for EmailFormatter."""

    def test_format_basic_email(self):
        """Test basic email formatting with default customer name."""
        formatter = EmailFormatter()
        content = "Your password has been reset successfully."

        result = formatter.format(content)

        assert "Dear Valued Customer" in result
        assert content in result
        assert "Best regards" in result
        assert "CloudStream CRM Support Team" in result
        assert "support@cloudstream.com" in result

    def test_format_email_with_customer_name(self):
        """Test email formatting with custom customer name."""
        formatter = EmailFormatter()
        content = "Your account has been upgraded."
        metadata = {"customer_name": "John Doe"}

        result = formatter.format(content, metadata)

        assert "Dear John Doe" in result
        assert content in result
        assert "Best regards" in result

    def test_format_email_structure(self):
        """Test email has proper structure with greeting, body, and signature."""
        formatter = EmailFormatter()
        content = "Test message"

        result = formatter.format(content)

        # Check structure order
        greeting_pos = result.find("Dear")
        content_pos = result.find(content)
        signature_pos = result.find("Best regards")

        assert greeting_pos < content_pos < signature_pos


# ============================================================================
# Tests for WhatsAppFormatter (T083)
# ============================================================================

@pytest.mark.unit
@pytest.mark.formatters
class TestWhatsAppFormatter:
    """Unit tests for WhatsAppFormatter."""

    def test_format_whatsapp_message(self):
        """Test WhatsApp formatting with emoji and brevity."""
        formatter = WhatsAppFormatter()
        content = "Your order has been shipped!"

        result = formatter.format(content)

        assert "👋" in result
        assert content in result
        assert "💬" in result
        assert "Need more help?" in result

    def test_format_whatsapp_concise(self):
        """Test WhatsApp formatter keeps messages concise."""
        formatter = WhatsAppFormatter()
        content = "Quick update"

        result = formatter.format(content)

        # WhatsApp messages should be relatively short
        assert len(result) < 200


# ============================================================================
# Tests for WebFormFormatter (T083)
# ============================================================================

@pytest.mark.unit
@pytest.mark.formatters
class TestWebFormFormatter:
    """Unit tests for WebFormFormatter."""

    def test_format_web_form_message(self):
        """Test web form formatting with structured content."""
        formatter = WebFormFormatter()
        content = "Your request has been processed."

        result = formatter.format(content)

        assert "**CloudStream CRM Support**" in result
        assert content in result
        assert "**Need additional assistance?**" in result
        assert "https://help.cloudstream.com" in result

    def test_format_web_form_has_links(self):
        """Test web form includes helpful links."""
        formatter = WebFormFormatter()
        content = "Test message"

        result = formatter.format(content)

        assert "help.cloudstream.com" in result
        assert "1-800-CLOUD-CRM" in result


# ============================================================================
# Tests for APIFormatter (T083)
# ============================================================================

@pytest.mark.unit
@pytest.mark.formatters
class TestAPIFormatter:
    """Unit tests for APIFormatter."""

    def test_format_api_minimal(self):
        """Test API formatter returns content with minimal changes."""
        formatter = APIFormatter()
        content = "Raw API response content"

        result = formatter.format(content)

        # API formatter should return content unchanged
        assert result == content

    def test_format_api_no_extra_formatting(self):
        """Test API formatter doesn't add extra formatting."""
        formatter = APIFormatter()
        content = "Simple message"

        result = formatter.format(content)

        # Should not add greetings, signatures, or emoji
        assert "Dear" not in result
        assert "Best regards" not in result
        assert "👋" not in result


# ============================================================================
# Tests for format_response function (T083)
# ============================================================================

@pytest.mark.unit
@pytest.mark.formatters
class TestFormatResponseFunction:
    """Unit tests for format_response helper function."""

    def test_format_response_email(self):
        """Test format_response with email channel."""
        content = "Test message"

        result = format_response(content, "email")

        assert "Dear" in result
        assert content in result

    def test_format_response_whatsapp(self):
        """Test format_response with WhatsApp channel."""
        content = "Test message"

        result = format_response(content, "whatsapp")

        assert "👋" in result
        assert content in result

    def test_format_response_web_form(self):
        """Test format_response with web form channel."""
        content = "Test message"

        result = format_response(content, "web_form")

        assert "**CloudStream CRM Support**" in result
        assert content in result

    def test_format_response_api(self):
        """Test format_response with API channel."""
        content = "Test message"

        result = format_response(content, "api")

        assert result == content

    def test_format_response_case_insensitive(self):
        """Test format_response handles case-insensitive channel names."""
        content = "Test message"

        result_upper = format_response(content, "EMAIL")
        result_lower = format_response(content, "email")

        assert result_upper == result_lower

    def test_format_response_invalid_channel(self):
        """Test format_response raises error for invalid channel."""
        content = "Test message"

        with pytest.raises(ValueError) as exc_info:
            format_response(content, "invalid_channel")

        assert "Unsupported channel" in str(exc_info.value)

    def test_format_response_with_metadata(self):
        """Test format_response passes metadata to formatter."""
        content = "Test message"
        metadata = {"customer_name": "Jane Smith"}

        result = format_response(content, "email", metadata)

        assert "Jane Smith" in result


# ============================================================================
# Tests for FORMATTERS registry (T083)
# ============================================================================

@pytest.mark.unit
@pytest.mark.formatters
class TestFormattersRegistry:
    """Unit tests for FORMATTERS registry."""

    def test_formatters_registry_has_all_channels(self):
        """Test FORMATTERS registry contains all expected channels."""
        expected_channels = ["email", "whatsapp", "web_form", "api"]

        for channel in expected_channels:
            assert channel in FORMATTERS

    def test_formatters_registry_instances(self):
        """Test FORMATTERS registry contains correct formatter instances."""
        assert isinstance(FORMATTERS["email"], EmailFormatter)
        assert isinstance(FORMATTERS["whatsapp"], WhatsAppFormatter)
        assert isinstance(FORMATTERS["web_form"], WebFormFormatter)
        assert isinstance(FORMATTERS["api"], APIFormatter)
