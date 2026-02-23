"""Test suite for customer identification functionality

Tests the identify_customer tool to verify:
1. Creating new customers with email only
2. Creating new customers with phone only
3. Creating new customers with both email and phone
4. Identifying existing customers by email
5. Identifying existing customers by phone
6. Retrieving customer history after identification

Note: In the file-based system, customers only exist if they have tickets.
"""

import pytest
import uuid
from src.tools import identify_customer_impl, lookup_customer_impl, create_support_ticket_impl


def generate_unique_email():
    """Generate a unique email address for testing."""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def generate_unique_phone():
    """Generate a unique phone number for testing."""
    return f"+1-555-{uuid.uuid4().hex[:4]}"


def test_create_customer_with_email_only():
    """Test creating a new customer with email only."""
    email = generate_unique_email()
    result = identify_customer_impl(email=email)
    assert result["is_new"] == True, "Should create new customer"
    assert "customer_id" in result
    assert result["customer_id"] is not None


def test_identify_existing_customer_by_email():
    """Test identifying an existing customer by email (one with a ticket)."""
    email = generate_unique_email()

    # Create customer by creating a ticket
    create_support_ticket_impl(
        customer_id=email,
        issue="Test issue",
        priority="normal",
        channel="web_form"
    )

    # Now identify the customer - should find them
    result = identify_customer_impl(email=email)
    assert result["is_new"] == False, "Should find existing customer"
    assert result["customer_id"] == email, "Should return same customer_id"


def test_create_customer_with_phone_only():
    """Test creating a new customer with phone only."""
    phone = generate_unique_phone()
    result = identify_customer_impl(phone=phone)
    assert result["is_new"] == True, "Should create new customer"
    assert "customer_id" in result
    assert result["customer_id"] is not None


def test_identify_existing_customer_by_phone():
    """Test identifying an existing customer by phone (one with a ticket)."""
    phone = generate_unique_phone()

    # Create customer by creating a ticket
    create_support_ticket_impl(
        customer_id=phone,
        issue="Test issue",
        priority="normal",
        channel="whatsapp"
    )

    # Now identify the customer - should find them
    result = identify_customer_impl(phone=phone)
    assert result["is_new"] == False, "Should find existing customer"
    assert result["customer_id"] == phone, "Should return same customer_id"


def test_create_customer_with_both_email_and_phone():
    """Test creating a new customer with both email and phone."""
    email = generate_unique_email()
    phone = generate_unique_phone()

    result = identify_customer_impl(email=email, phone=phone)
    assert result["is_new"] == True, "Should create new customer"
    assert "customer_id" in result
    assert result["customer_id"] is not None


def test_identify_by_email_when_both_exist():
    """Test identifying by email when customer has both email and phone."""
    email = generate_unique_email()
    phone = generate_unique_phone()

    # Create customer by creating a ticket with both identifiers
    create_support_ticket_impl(
        customer_id=email,
        issue="Test issue",
        priority="normal",
        channel="web_form"
    )

    # Identify by email only
    result = identify_customer_impl(email=email)
    assert result["is_new"] == False, "Should find existing customer"
    assert result["email"] == email, "Should have correct email"


def test_identify_by_phone_when_both_exist():
    """Test identifying by phone when customer has both email and phone."""
    email = generate_unique_email()
    phone = generate_unique_phone()

    # Create customer by creating a ticket with phone
    create_support_ticket_impl(
        customer_id=phone,
        issue="Test issue",
        priority="normal",
        channel="whatsapp"
    )

    # Identify by phone only
    result = identify_customer_impl(phone=phone)
    assert result["is_new"] == False, "Should find existing customer"
    assert result["phone"] == phone, "Should have correct phone"


def test_get_customer_history_after_identification():
    """Test retrieving customer history after identification."""
    email = generate_unique_email()

    # Create customer by creating a ticket
    create_support_ticket_impl(
        customer_id=email,
        issue="Test issue",
        priority="normal",
        channel="web_form"
    )

    # Get history
    history = lookup_customer_impl(email)
    assert history["customer_id"] == email
    assert "email" in history
    assert "plan_type" in history
    assert "support_tickets" in history
    assert len(history["support_tickets"]) > 0, "Should have at least one ticket"


def test_error_handling_no_identifiers():
    """Test error handling when no identifiers are provided."""
    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        identify_customer_impl()
