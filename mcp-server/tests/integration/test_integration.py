import pytest
import uuid
from src.tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    lookup_customer_impl,
    escalate_ticket_impl,
    save_reply_impl,
    analyze_sentiment_impl,
    identify_customer_impl
)


def test_end_to_end_workflow():
    """Test the complete workflow of customer support operations."""
    # Generate unique identifiers for this test
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+1-555-{uuid.uuid4().hex[:4]}"

    # Step 1: Identify customer (NEW - first step in workflow)
    identify_result = identify_customer_impl(email=email, phone=phone)
    assert isinstance(identify_result, dict)
    assert "customer_id" in identify_result
    assert "is_new" in identify_result
    customer_id = identify_result["customer_id"]

    # Step 2: Analyze sentiment of incoming message
    message = "I need help with pricing information for my project."
    sentiment_result = analyze_sentiment_impl(message)
    assert isinstance(sentiment_result, dict)
    assert "sentiment_score" in sentiment_result
    assert "sentiment_label" in sentiment_result

    # Step 3: Search for knowledge base information
    kb_result = search_product_docs_impl("product pricing information")
    assert isinstance(kb_result, list)
    assert len(kb_result) > 0  # Should return at least one result

    # Step 4: Create a support ticket for the customer
    ticket_result = create_support_ticket_impl(customer_id, "Need help with pricing", "normal", "web_form")
    assert isinstance(ticket_result, dict)
    assert "ticket_id" in ticket_result

    # Step 5: Get customer history
    history_result = lookup_customer_impl(customer_id)
    assert isinstance(history_result, dict)
    assert "customer_id" in history_result
    assert history_result["customer_id"] == customer_id

    # Step 6: Extract ticket ID from the create_ticket response for further operations
    ticket_id = ticket_result["ticket_id"]

    # Step 7: Send a response to the ticket
    response_result = save_reply_impl(ticket_id, "Thank you for contacting support. We will review your query.", "web_form")
    assert isinstance(response_result, dict)
    assert response_result["ticket_id"] == ticket_id


def test_end_to_end_workflow_with_escalation():
    """Test workflow that triggers escalation."""
    # Generate unique identifiers
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Step 1: Identify customer
    identify_result = identify_customer_impl(email=email)
    customer_id = identify_result["customer_id"]

    # Step 2: Analyze very negative sentiment (should trigger escalation)
    message = "This is terrible! I'm extremely frustrated and want a refund immediately!"
    sentiment_result = analyze_sentiment_impl(message)
    assert sentiment_result["sentiment_score"] < 0.3  # Should be below escalation threshold

    # Step 3: Create urgent ticket
    ticket_result = create_support_ticket_impl(customer_id, "Urgent refund request", "urgent", "email")
    ticket_id = ticket_result["ticket_id"]

    # Step 4: Escalate to human (based on negative sentiment)
    escalate_result = escalate_ticket_impl(ticket_id, "Customer sentiment very negative, requires immediate attention")
    assert isinstance(escalate_result, dict)
    assert "escalation_id" in escalate_result
    assert escalate_result["status"] == "escalated"


def test_cross_channel_customer_identification():
    """Test customer identification across multiple channels."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+1-555-{uuid.uuid4().hex[:4]}"

    # First contact via email (new customer)
    result1 = identify_customer_impl(email=email)
    customer_id_email = result1["customer_id"]
    assert result1["is_new"] == True

    # Create a ticket to establish the customer in the system
    create_support_ticket_impl(
        customer_id=email,
        issue="Initial contact",
        priority="normal",
        channel="email"
    )

    # Second contact via same email (should find existing)
    result2 = identify_customer_impl(email=email)
    assert result2["is_new"] == False
    assert result2["customer_id"] == customer_id_email

    # Third contact with both email and phone (should find existing by email)
    result3 = identify_customer_impl(email=email, phone=phone)
    assert result3["is_new"] == False
    assert result3["email"] == email


def test_error_handling_workflow():
    """Test that errors are properly handled in the workflow."""
    # Test invalid inputs that should trigger error handling

    # Empty customer_id
    with pytest.raises(ValueError, match="Customer ID must be a non-empty string"):
        create_support_ticket_impl("", "Test issue", "normal", "web_form")

    # Empty issue
    with pytest.raises(ValueError, match="Issue must be a non-empty string"):
        create_support_ticket_impl("customer_123", "", "normal", "web_form")

    # Invalid priority
    with pytest.raises(ValueError, match="Priority must be one of"):
        create_support_ticket_impl("customer_123", "Test issue", "invalid", "web_form")

    # Invalid channel
    with pytest.raises(ValueError, match="Channel must be one of"):
        create_support_ticket_impl("customer_123", "Test issue", "normal", "invalid")

    # Empty customer_id for lookup
    with pytest.raises(ValueError, match="Customer ID must be a non-empty string"):
        lookup_customer_impl("")

    # Empty ticket_id for escalation
    with pytest.raises(ValueError, match="Ticket ID must be a non-empty string"):
        escalate_ticket_impl("", "Test reason")

    # Empty reason for escalation
    with pytest.raises(ValueError, match="Reason must be a non-empty string"):
        escalate_ticket_impl("ticket_123", "")

    # Non-existent ticket for escalation
    with pytest.raises(ValueError, match="Ticket with ID .* not found"):
        escalate_ticket_impl("nonexistent_ticket", "Test reason")

    # Empty ticket_id for send_response
    with pytest.raises(ValueError, match="Ticket ID must be a non-empty string"):
        save_reply_impl("", "Test message", "web_form")

    # Empty message for send_response
    with pytest.raises(ValueError, match="Message must be a non-empty string"):
        save_reply_impl("ticket_123", "", "web_form")

    # No identifiers for identify_customer
    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        identify_customer_impl()

    # Empty query for search
    with pytest.raises(ValueError):
        search_product_docs_impl("")

    # Invalid max_results for search
    with pytest.raises(ValueError):
        search_product_docs_impl("test", max_results=-1)

    with pytest.raises(ValueError):
        search_product_docs_impl("test", max_results=25)


def test_tool_consistency():
    """Test that all tools return consistent responses."""
    # Generate unique identifiers
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Test identify_customer
    identify_result = identify_customer_impl(email=email)
    assert isinstance(identify_result, dict)
    assert "customer_id" in identify_result
    assert "is_new" in identify_result
    customer_id = identify_result["customer_id"]

    # Test analyze_sentiment
    sentiment_result = analyze_sentiment_impl("Test message")
    assert isinstance(sentiment_result, dict)
    assert "sentiment_score" in sentiment_result
    assert "sentiment_label" in sentiment_result

    # Test search
    search_result = search_product_docs_impl("test query")
    assert isinstance(search_result, list)

    # Test create_ticket
    ticket_result = create_support_ticket_impl(customer_id, "test issue")
    assert isinstance(ticket_result, dict)
    assert "ticket_id" in ticket_result
    ticket_id = ticket_result["ticket_id"]

    # Test lookup_customer
    customer_result = lookup_customer_impl(customer_id)
    assert isinstance(customer_result, dict)
    assert "customer_id" in customer_result

    # Test escalate_ticket
    escalate_result = escalate_ticket_impl(ticket_id, "test reason")
    assert isinstance(escalate_result, dict)
    assert "escalation_id" in escalate_result

    # Test send_response
    response_result = save_reply_impl(ticket_id, "test message")
    assert isinstance(response_result, dict)
    assert "ticket_id" in response_result


def test_sentiment_driven_workflow():
    """Test workflow where sentiment analysis drives escalation decision."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Identify customer
    identify_result = identify_customer_impl(email=email)
    customer_id = identify_result["customer_id"]

    # Test positive sentiment - no escalation needed
    positive_message = "I love your product! Everything works great!"
    positive_sentiment = analyze_sentiment_impl(positive_message)
    assert positive_sentiment["sentiment_score"] > 0.7
    assert positive_sentiment["sentiment_label"] == "positive"

    # Create ticket with positive sentiment
    ticket1 = create_support_ticket_impl(customer_id, positive_message, "low", "email")
    # No escalation needed - just send response
    save_reply_impl(ticket1["ticket_id"], "Thank you for your feedback!", "email")

    # Test negative sentiment - escalation needed
    negative_message = "This is terrible! I'm extremely frustrated and angry!"
    negative_sentiment = analyze_sentiment_impl(negative_message)
    assert negative_sentiment["sentiment_score"] < 0.3  # Below escalation threshold
    assert negative_sentiment["sentiment_label"] == "negative"

    # Create ticket with negative sentiment
    ticket2 = create_support_ticket_impl(customer_id, negative_message, "urgent", "email")
    # Escalate due to negative sentiment
    escalate_ticket_impl(ticket2["ticket_id"], f"Customer sentiment very negative (score: {negative_sentiment['sentiment_score']})")


if __name__ == "__main__":
    pytest.main([__file__])
