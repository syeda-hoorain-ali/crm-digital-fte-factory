import pytest
from src.tools.crm_tools import (
    search_product_docs_impl,
    create_support_ticket_impl,
    lookup_customer_impl,
    escalate_ticket_impl,
    save_reply_impl,
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
