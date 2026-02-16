import pytest
from src.tools.crm_tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    lookup_customer_impl,
    escalate_ticket_impl,
    save_reply_impl
)


def test_end_to_end_workflow():
    """Test the complete workflow of customer support operations."""
    # Step 1: Search for knowledge base information
    kb_result = search_product_docs_impl("product pricing information")
    assert isinstance(kb_result, list)
    assert len(kb_result) > 0  # Should return at least one result

    # Step 2: Create a support ticket for the customer
    ticket_result = create_support_ticket_impl("customer_test_001", "Need help with pricing", "normal", "web_form")
    assert isinstance(ticket_result, dict)
    assert "ticket_id" in ticket_result

    # Step 3: Get customer history
    history_result = lookup_customer_impl("customer_test_001")
    assert isinstance(history_result, dict)
    assert "customer_id" in history_result

    # Step 4: Extract ticket ID from the create_ticket response for further operations
    ticket_id = ticket_result["ticket_id"]

    # Step 5: Send a response to the ticket
    response_result = save_reply_impl(ticket_id, "Thank you for contacting support. We will review your query.", "web_form")
    assert isinstance(response_result, dict)
    assert response_result["ticket_id"] == ticket_id


def test_error_handling_workflow():
    """Test that errors are properly handled in the workflow."""
    # Test invalid inputs that should trigger error handling
    with pytest.raises(Exception):
        create_support_ticket_impl("", "", "", "")

    with pytest.raises(Exception):
        lookup_customer_impl("")


def test_tool_consistency():
    """Test that all tools return consistent responses."""
    # Test that the functions work correctly and return expected types
    search_result = search_product_docs_impl("test query")
    assert isinstance(search_result, list)

    ticket_result = create_support_ticket_impl("cust_001", "test issue")
    assert isinstance(ticket_result, dict)
    ticket_id = ticket_result["ticket_id"]

    customer_result = lookup_customer_impl("cust_001")
    assert isinstance(customer_result, dict)

    escalate_result = escalate_ticket_impl(ticket_id, "test reason")
    assert isinstance(escalate_result, dict)

    response_result = save_reply_impl(ticket_id, "test message")
    assert isinstance(response_result, dict)


if __name__ == "__main__":
    pytest.main([__file__])
