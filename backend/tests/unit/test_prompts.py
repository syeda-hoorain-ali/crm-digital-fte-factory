"""Unit tests for prompt template rendering."""

import pytest

from src.agent.prompts import (
    SENTIMENT_ANALYSIS_PROMPT,
    CUSTOMER_IDENTIFICATION_PROMPT,
    KNOWLEDGE_RETRIEVAL_PROMPT,
    ESCALATION_DECISION_PROMPT,
    CHANNEL_ADAPTATION_PROMPT,
)


# ============================================================================
# Tests for Prompt Templates (T084)
# ============================================================================

@pytest.mark.unit
class TestPromptTemplates:
    """Unit tests for prompt template content and structure."""

    def test_sentiment_analysis_prompt_exists(self):
        """Test sentiment analysis prompt is defined."""
        assert SENTIMENT_ANALYSIS_PROMPT is not None
        assert len(SENTIMENT_ANALYSIS_PROMPT) > 0

    def test_sentiment_analysis_prompt_content(self):
        """Test sentiment analysis prompt contains key instructions."""
        prompt = SENTIMENT_ANALYSIS_PROMPT.lower()

        # Should mention sentiment analysis
        assert "sentiment" in prompt

        # Should mention emotional states
        assert any(word in prompt for word in ["frustration", "anger", "negative"])

    def test_customer_identification_prompt_exists(self):
        """Test customer identification prompt is defined."""
        assert CUSTOMER_IDENTIFICATION_PROMPT is not None
        assert len(CUSTOMER_IDENTIFICATION_PROMPT) > 0

    def test_customer_identification_prompt_content(self):
        """Test customer identification prompt contains key instructions."""
        prompt = CUSTOMER_IDENTIFICATION_PROMPT.lower()

        # Should mention customer identification
        assert "customer" in prompt or "identify" in prompt

        # Should mention contact information
        assert any(word in prompt for word in ["email", "phone", "contact"])

    def test_knowledge_retrieval_prompt_exists(self):
        """Test knowledge retrieval prompt is defined."""
        assert KNOWLEDGE_RETRIEVAL_PROMPT is not None
        assert len(KNOWLEDGE_RETRIEVAL_PROMPT) > 0

    def test_knowledge_retrieval_prompt_content(self):
        """Test knowledge retrieval prompt contains key instructions."""
        prompt = KNOWLEDGE_RETRIEVAL_PROMPT.lower()

        # Should mention knowledge base or search
        assert any(word in prompt for word in ["knowledge", "search", "article", "documentation"])

    def test_escalation_decision_prompt_exists(self):
        """Test escalation decision prompt is defined."""
        assert ESCALATION_DECISION_PROMPT is not None
        assert len(ESCALATION_DECISION_PROMPT) > 0

    def test_escalation_decision_prompt_content(self):
        """Test escalation decision prompt contains key instructions."""
        prompt = ESCALATION_DECISION_PROMPT.lower()

        # Should mention escalation
        assert "escalat" in prompt

        # Should mention human or agent
        assert any(word in prompt for word in ["human", "agent", "support"])

    def test_channel_adaptation_prompt_exists(self):
        """Test channel adaptation prompt is defined."""
        assert CHANNEL_ADAPTATION_PROMPT is not None
        assert len(CHANNEL_ADAPTATION_PROMPT) > 0

    def test_channel_adaptation_prompt_content(self):
        """Test channel adaptation prompt contains key instructions."""
        prompt = CHANNEL_ADAPTATION_PROMPT.lower()

        # Should mention channels or formatting
        assert any(word in prompt for word in ["channel", "format", "adapt"])

    def test_all_prompts_are_strings(self):
        """Test all prompts are string type."""
        prompts = [
            SENTIMENT_ANALYSIS_PROMPT,
            CUSTOMER_IDENTIFICATION_PROMPT,
            KNOWLEDGE_RETRIEVAL_PROMPT,
            ESCALATION_DECISION_PROMPT,
            CHANNEL_ADAPTATION_PROMPT,
        ]

        for prompt in prompts:
            assert isinstance(prompt, str)

    def test_prompts_are_not_empty(self):
        """Test all prompts have meaningful content."""
        prompts = [
            SENTIMENT_ANALYSIS_PROMPT,
            CUSTOMER_IDENTIFICATION_PROMPT,
            KNOWLEDGE_RETRIEVAL_PROMPT,
            ESCALATION_DECISION_PROMPT,
            CHANNEL_ADAPTATION_PROMPT,
        ]

        for prompt in prompts:
            # Each prompt should have at least 50 characters
            assert len(prompt) >= 50
