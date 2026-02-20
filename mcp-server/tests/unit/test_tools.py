import pytest
import uuid
from src.tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    lookup_customer_impl,
    escalate_ticket_impl,
    save_reply_impl,
    analyze_sentiment_impl,
    identify_customer_impl,
)


def test_search_product_docs_impl():
    """Test the search_product_docs_impl function."""
    result = search_product_docs_impl("test query")
    assert isinstance(result, list)  # Should return a list of results


def test_search_product_docs_impl_empty_query():
    """Test the search_product_docs_impl function with empty query."""
    with pytest.raises(ValueError):
        search_product_docs_impl("")


def test_create_support_ticket_impl():
    """Test the create_support_ticket_impl function."""
    result = create_support_ticket_impl("customer_123", "Test issue description")
    assert isinstance(result, dict)  # Should return a dictionary
    assert result["customer_id"] == "customer_123"


def test_create_support_ticket_impl_with_priority():
    """Test the create_support_ticket_impl function with priority specified."""
    result = create_support_ticket_impl("customer_456", "Test issue", "high")
    assert isinstance(result, dict)  # Should return a dictionary
    assert result["priority"] == "high"


def test_create_support_ticket_impl_with_channel():
    """Test the create_support_ticket_impl function with channel specified."""
    result = create_support_ticket_impl("customer_789", "Test issue", "normal", "email")
    assert isinstance(result, dict)  # Should return a dictionary
    assert result["channel"] == "email"


def test_lookup_customer_impl():
    """Test the lookup_customer_impl function."""
    # First create a customer to look up
    create_support_ticket_impl("customer_123", "Test issue description")
    result = lookup_customer_impl("customer_123")
    assert isinstance(result, dict)  # Should return a dictionary
    assert result["customer_id"] == "customer_123"


def test_escalate_ticket_impl():
    """Test the escalate_ticket_impl function."""
    # First create a ticket to escalate
    ticket_result = create_support_ticket_impl("customer_123", "Test issue description")
    ticket_id = ticket_result["ticket_id"]
    result = escalate_ticket_impl(ticket_id, "Issue requires human attention")
    assert isinstance(result, dict)  # Should return a dictionary
    assert "escalation_id" in result


def test_save_reply_impl():
    """Test the save_reply_impl function."""
    # First create a ticket for the reply
    ticket_result = create_support_ticket_impl("customer_123", "Test issue description")
    ticket_id = ticket_result["ticket_id"]
    result = save_reply_impl(ticket_id, "Thank you for contacting support.")
    assert isinstance(result, dict)  # Should return a dictionary
    assert result["ticket_id"] == ticket_id


def test_analyze_sentiment_impl_positive():
    """Test sentiment analysis with positive message."""
    result = analyze_sentiment_impl("I love this product! It works perfectly!")
    assert isinstance(result, dict)
    assert "sentiment_score" in result
    assert "confidence" in result
    assert "sentiment_label" in result
    assert result["sentiment_label"] == "positive"
    assert result["sentiment_score"] > 0.7  # Should be highly positive


def test_analyze_sentiment_impl_negative():
    """Test sentiment analysis with negative message."""
    result = analyze_sentiment_impl("This is terrible. I want a refund immediately.")
    assert isinstance(result, dict)
    assert result["sentiment_label"] == "negative"
    assert result["sentiment_score"] < 0.5  # Should be negative


def test_analyze_sentiment_impl_very_negative():
    """Test sentiment analysis with very negative message (escalation trigger)."""
    result = analyze_sentiment_impl("I am extremely frustrated and angry with your support team!")
    assert isinstance(result, dict)
    assert result["sentiment_label"] == "negative"
    assert result["sentiment_score"] < 0.3  # Should trigger escalation threshold


def test_analyze_sentiment_impl_neutral():
    """Test sentiment analysis with neutral message."""
    result = analyze_sentiment_impl("The service is okay, nothing special.")
    assert isinstance(result, dict)
    assert result["sentiment_label"] in ["neutral", "negative"]  # Could be either
    assert 0.3 <= result["sentiment_score"] <= 0.6  # Should be in neutral range


def test_analyze_sentiment_impl_empty_string():
    """Test sentiment analysis with empty string."""
    result = analyze_sentiment_impl("")
    assert isinstance(result, dict)
    assert result["sentiment_score"] == 0.5  # Should return neutral
    assert result["confidence"] == 0.0  # No confidence for empty text
    assert result["sentiment_label"] == "neutral"
    assert "note" in result  # Should have a note explaining the empty string


def test_analyze_sentiment_impl_whitespace_only():
    """Test sentiment analysis with whitespace-only string."""
    result = analyze_sentiment_impl("   \n\t  ")
    assert isinstance(result, dict)
    assert result["sentiment_score"] == 0.5  # Should return neutral
    assert result["confidence"] == 0.0
    assert result["sentiment_label"] == "neutral"


def test_analyze_sentiment_impl_output_structure():
    """Test that sentiment analysis returns all required fields."""
    result = analyze_sentiment_impl("Test message")
    assert isinstance(result, dict)
    # Check all required fields are present
    assert "sentiment_score" in result
    assert "confidence" in result
    assert "sentiment_label" in result
    assert "raw_scores" in result
    # Check raw_scores structure
    assert "neg" in result["raw_scores"]
    assert "neu" in result["raw_scores"]
    assert "pos" in result["raw_scores"]
    assert "compound" in result["raw_scores"]
    # Check value ranges
    assert 0.0 <= result["sentiment_score"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0


# ============================================================================
# identify_customer Tests
# ============================================================================

def test_identify_customer_impl_with_email():
    """Test identifying customer with email only."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    result = identify_customer_impl(email=email)
    assert isinstance(result, dict)
    assert "customer_id" in result
    assert "is_new" in result
    assert result["is_new"] == True


def test_identify_customer_impl_with_phone():
    """Test identifying customer with phone only."""
    phone = f"+1-555-{uuid.uuid4().hex[:4]}"
    result = identify_customer_impl(phone=phone)
    assert isinstance(result, dict)
    assert "customer_id" in result
    assert "is_new" in result
    assert result["is_new"] == True


def test_identify_customer_impl_with_both():
    """Test identifying customer with both email and phone."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+1-555-{uuid.uuid4().hex[:4]}"
    result = identify_customer_impl(email=email, phone=phone)
    assert isinstance(result, dict)
    assert "customer_id" in result
    assert "is_new" in result
    assert result["is_new"] == True


def test_identify_customer_impl_existing_customer():
    """Test identifying an existing customer."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    # Create customer
    result1 = identify_customer_impl(email=email)
    customer_id = result1["customer_id"]
    # Identify same customer
    result2 = identify_customer_impl(email=email)
    assert result2["is_new"] == False
    assert result2["customer_id"] == customer_id


def test_identify_customer_impl_no_identifiers():
    """Test error when no identifiers provided."""
    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        identify_customer_impl()


def test_identify_customer_impl_empty_strings():
    """Test error when empty strings provided."""
    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        identify_customer_impl(email="", phone="")


def test_identify_customer_impl_whitespace_only():
    """Test error when whitespace-only strings provided."""
    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        identify_customer_impl(email="   ", phone="   ")


# ============================================================================
# Error Case Tests for All Tools
# ============================================================================

def test_create_ticket_invalid_priority():
    """Test create_ticket with invalid priority."""
    with pytest.raises(ValueError, match="Priority must be one of"):
        create_support_ticket_impl("customer_123", "Test issue", "invalid_priority")


def test_create_ticket_invalid_channel():
    """Test create_ticket with invalid channel."""
    with pytest.raises(ValueError, match="Channel must be one of"):
        create_support_ticket_impl("customer_123", "Test issue", "normal", "invalid_channel")


def test_create_ticket_empty_customer_id():
    """Test create_ticket with empty customer_id."""
    with pytest.raises(ValueError, match="Customer ID must be a non-empty string"):
        create_support_ticket_impl("", "Test issue")


def test_create_ticket_empty_issue():
    """Test create_ticket with empty issue."""
    with pytest.raises(ValueError, match="Issue must be a non-empty string"):
        create_support_ticket_impl("customer_123", "")


def test_lookup_customer_empty_id():
    """Test lookup_customer with empty customer_id."""
    with pytest.raises(ValueError, match="Customer ID must be a non-empty string"):
        lookup_customer_impl("")


def test_escalate_ticket_empty_ticket_id():
    """Test escalate_ticket with empty ticket_id."""
    with pytest.raises(ValueError, match="Ticket ID must be a non-empty string"):
        escalate_ticket_impl("", "Test reason")


def test_escalate_ticket_empty_reason():
    """Test escalate_ticket with empty reason."""
    with pytest.raises(ValueError, match="Reason must be a non-empty string"):
        escalate_ticket_impl("ticket_123", "")


def test_escalate_ticket_nonexistent_ticket():
    """Test escalate_ticket with non-existent ticket_id."""
    with pytest.raises(ValueError, match="Ticket with ID .* not found"):
        escalate_ticket_impl("nonexistent_ticket_id", "Test reason")


def test_send_response_empty_ticket_id():
    """Test send_response with empty ticket_id."""
    with pytest.raises(ValueError, match="Ticket ID must be a non-empty string"):
        save_reply_impl("", "Test message")


def test_send_response_empty_message():
    """Test send_response with empty message."""
    with pytest.raises(ValueError, match="Message must be a non-empty string"):
        save_reply_impl("ticket_123", "")


def test_send_response_invalid_channel():
    """Test send_response with invalid channel."""
    # First create a ticket
    ticket_result = create_support_ticket_impl("customer_123", "Test issue")
    ticket_id = ticket_result["ticket_id"]
    with pytest.raises(ValueError, match="Channel must be one of"):
        save_reply_impl(ticket_id, "Test message", "invalid_channel")


def test_send_response_nonexistent_ticket():
    """Test send_response with non-existent ticket_id."""
    with pytest.raises(ValueError, match="Ticket with ID .* not found"):
        save_reply_impl("nonexistent_ticket_id", "Test message")


def test_search_knowledge_base_invalid_max_results_negative():
    """Test search_knowledge_base with negative max_results."""
    with pytest.raises(ValueError):
        search_product_docs_impl("test query", max_results=-1)


def test_search_knowledge_base_invalid_max_results_too_large():
    """Test search_knowledge_base with max_results > 20."""
    with pytest.raises(ValueError):
        search_product_docs_impl("test query", max_results=25)


def test_search_knowledge_base_very_long_query():
    """Test search_knowledge_base with very long query (>1000 chars)."""
    long_query = "a" * 1001
    with pytest.raises(ValueError):
        search_product_docs_impl(long_query)


def test_analyze_sentiment_very_long_message():
    """Test analyze_sentiment with very long message (>10000 chars)."""
    long_message = "a" * 10001
    with pytest.raises(ValueError):
        analyze_sentiment_impl(long_message)
