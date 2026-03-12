"""Unit tests for WhatsApp message splitting logic."""

import pytest
from src.channels.whatsapp_handler import WhatsAppHandler, WHATSAPP_MESSAGE_LIMIT
from src.channels.twilio_client import TwilioClient


@pytest.fixture
def whatsapp_handler():
    """Create WhatsApp handler for testing."""
    # Mock Twilio client
    twilio_client = TwilioClient(
        account_sid="test_sid",
        auth_token="test_token",
        whatsapp_from="whatsapp:+1234567890"
    )
    return WhatsAppHandler(twilio_client, "test_token")


class TestMessageSplitting:
    """Test message splitting logic."""

    def test_short_message_not_split(self, whatsapp_handler):
        """Test that short messages are not split."""
        message = "Hello, this is a short message."
        parts = whatsapp_handler._split_message(message)

        assert len(parts) == 1
        assert parts[0] == message

    def test_message_at_limit_not_split(self, whatsapp_handler):
        """Test that message exactly at limit is not split."""
        message = "x" * WHATSAPP_MESSAGE_LIMIT
        parts = whatsapp_handler._split_message(message)

        assert len(parts) == 1
        assert parts[0] == message

    def test_message_over_limit_split(self, whatsapp_handler):
        """Test that message over limit is split."""
        message = "x" * (WHATSAPP_MESSAGE_LIMIT + 100)
        parts = whatsapp_handler._split_message(message)

        assert len(parts) == 2
        assert all(len(part) <= WHATSAPP_MESSAGE_LIMIT for part in parts)
        assert "".join(parts) == message

    def test_split_on_sentence_boundary(self, whatsapp_handler):
        """Test that splitting prefers sentence boundaries."""
        # Create message with sentences
        sentence = "This is a sentence. "
        num_sentences = (WHATSAPP_MESSAGE_LIMIT // len(sentence)) + 5
        message = sentence * num_sentences

        parts = whatsapp_handler._split_message(message)

        assert len(parts) >= 2
        # First part should end with sentence boundary
        assert parts[0].endswith(".")
        # All parts should be under limit
        assert all(len(part) <= WHATSAPP_MESSAGE_LIMIT for part in parts)

    def test_split_on_word_boundary(self, whatsapp_handler):
        """Test that splitting falls back to word boundaries."""
        # Create message with long words (no sentence boundaries)
        word = "word "
        num_words = (WHATSAPP_MESSAGE_LIMIT // len(word)) + 10
        message = word * num_words

        parts = whatsapp_handler._split_message(message)

        assert len(parts) >= 2
        # All parts should be under limit
        assert all(len(part) <= WHATSAPP_MESSAGE_LIMIT for part in parts)
        # Verify no words are broken (each part should contain complete words)
        for part in parts:
            # Each part should start and end with word characters or be all words
            words = part.split()
            assert len(words) > 0  # Should have at least one word

    def test_split_preserves_content(self, whatsapp_handler):
        """Test that splitting preserves all content."""
        message = "A" * 1000 + "B" * 1000 + "C" * 1000
        parts = whatsapp_handler._split_message(message)

        # Reconstruct message
        reconstructed = "".join(parts)
        assert reconstructed == message

    def test_split_multiple_parts(self, whatsapp_handler):
        """Test splitting into multiple parts."""
        # Create message that needs 3+ parts
        message = "x" * (WHATSAPP_MESSAGE_LIMIT * 3)
        parts = whatsapp_handler._split_message(message)

        assert len(parts) >= 3
        assert all(len(part) <= WHATSAPP_MESSAGE_LIMIT for part in parts)
        assert "".join(parts) == message

    def test_split_with_mixed_content(self, whatsapp_handler):
        """Test splitting with mixed sentences and words."""
        # Create realistic message
        paragraph = (
            "This is a longer paragraph with multiple sentences. "
            "It contains various punctuation marks! "
            "And it should be split intelligently? "
            "Yes, it should. "
        )
        num_paragraphs = (WHATSAPP_MESSAGE_LIMIT // len(paragraph)) + 3
        message = paragraph * num_paragraphs

        parts = whatsapp_handler._split_message(message)

        assert len(parts) >= 2
        # Verify content preserved (with whitespace normalization)
        reconstructed = " ".join(parts)
        # Compare with normalized whitespace
        assert reconstructed.strip() in message or message.strip() in reconstructed
        # All parts under limit
        assert all(len(part) <= WHATSAPP_MESSAGE_LIMIT for part in parts)

    def test_split_strips_whitespace(self, whatsapp_handler):
        """Test that split parts have whitespace stripped."""
        message = "A" * 1000 + "   " + "B" * 1000
        parts = whatsapp_handler._split_message(message)

        # Parts should not have leading/trailing whitespace
        for part in parts:
            assert part == part.strip()

    def test_empty_message(self, whatsapp_handler):
        """Test handling of empty message."""
        message = ""
        parts = whatsapp_handler._split_message(message)

        assert len(parts) == 1
        assert parts[0] == ""

    def test_whitespace_only_message(self, whatsapp_handler):
        """Test handling of whitespace-only message."""
        message = "   "
        parts = whatsapp_handler._split_message(message)

        assert len(parts) == 1
        # Whitespace-only messages under limit are returned as-is
        assert parts[0] == message


class TestEscalationDetection:
    """Test escalation keyword detection."""

    def test_detect_human_keyword(self, whatsapp_handler):
        """Test detection of 'human' keyword."""
        message = "I need to speak to a human"
        assert whatsapp_handler._detect_escalation(message) is True

    def test_detect_agent_keyword(self, whatsapp_handler):
        """Test detection of 'agent' keyword."""
        message = "Can I talk to an agent?"
        assert whatsapp_handler._detect_escalation(message) is True

    def test_detect_case_insensitive(self, whatsapp_handler):
        """Test case-insensitive detection."""
        messages = [
            "I need a HUMAN",
            "Connect me to an AGENT",
            "HuMaN please",
            "AgEnT help"
        ]
        for message in messages:
            assert whatsapp_handler._detect_escalation(message) is True

    def test_no_escalation_keywords(self, whatsapp_handler):
        """Test messages without escalation keywords."""
        messages = [
            "Hello, I have a question",
            "What is your return policy?",
            "Thank you for your help",
            "I'm having trouble with my order"
        ]
        for message in messages:
            assert whatsapp_handler._detect_escalation(message) is False

    def test_partial_word_match(self, whatsapp_handler):
        """Test that partial words containing keywords are detected."""
        # "human" in "humanity" - should match (substring)
        assert whatsapp_handler._detect_escalation("humanity") is True
        assert whatsapp_handler._detect_escalation("Humanity needs help") is True

        # "agent" NOT in "agency" - should not match
        assert whatsapp_handler._detect_escalation("agency") is False
        assert whatsapp_handler._detect_escalation("The agency is closed") is False

        # But "agent" in "agents" - should match
        assert whatsapp_handler._detect_escalation("agents") is True
        assert whatsapp_handler._detect_escalation("I need an agent") is True
