"""Test suite for customer identification functionality

Tests the identify_customer tool to verify:
1. Creating new customers with email only
2. Creating new customers with phone only
3. Creating new customers with both email and phone
4. Identifying existing customers by email
5. Identifying existing customers by phone
6. Retrieving customer history after identification
"""

import pytest
import uuid
from src.tools import identify_customer_impl, lookup_customer_impl


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
    """Test identifying an existing customer by email."""
    email = generate_unique_email()

    # Create customer
    result1 = identify_customer_impl(email=email)
    customer_id = result1["customer_id"]

    # Identify same customer
    result2 = identify_customer_impl(email=email)
    assert result2["is_new"] == False, "Should find existing customer"
    assert result2["customer_id"] == customer_id, "Should return same customer_id"


def test_create_customer_with_phone_only():
    """Test creating a new customer with phone only."""
    phone = generate_unique_phone()
    result = identify_customer_impl(phone=phone)
    assert result["is_new"] == True, "Should create new customer"
    assert "customer_id" in result
    assert result["customer_id"] is not None


def test_identify_existing_customer_by_phone():
    """Test identifying an existing customer by phone."""
    phone = generate_unique_phone()

    # Create customer
    result1 = identify_customer_impl(phone=phone)
    customer_id = result1["customer_id"]

    # Identify same customer
    result2 = identify_customer_impl(phone=phone)
    assert result2["is_new"] == False, "Should find existing customer"
    assert result2["customer_id"] == customer_id, "Should return same customer_id"


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

    # Create customer with both
    result1 = identify_customer_impl(email=email, phone=phone)
    customer_id = result1["customer_id"]

    # Identify by email only
    result2 = identify_customer_impl(email=email)
    assert result2["is_new"] == False, "Should find existing customer"
    assert result2["customer_id"] == customer_id, "Should return same customer_id"


def test_identify_by_phone_when_both_exist():
    """Test identifying by phone when customer has both email and phone."""
    email = generate_unique_email()
    phone = generate_unique_phone()

    # Create customer with both
    result1 = identify_customer_impl(email=email, phone=phone)
    customer_id = result1["customer_id"]

    # Identify by phone only
    result2 = identify_customer_impl(phone=phone)
    assert result2["is_new"] == False, "Should find existing customer"
    assert result2["customer_id"] == customer_id, "Should return same customer_id"


def test_get_customer_history_after_identification():
    """Test retrieving customer history after identification."""
    email = generate_unique_email()
    phone = generate_unique_phone()

    # Create customer
    result = identify_customer_impl(email=email, phone=phone)
    customer_id = result["customer_id"]

    # Get history
    history = lookup_customer_impl(customer_id)
    assert history["customer_id"] == customer_id
    assert "email" in history
    assert "plan_type" in history
    assert "support_tickets" in history


def test_error_handling_no_identifiers():
    """Test error handling when no identifiers are provided."""
    with pytest.raises(ValueError, match="At least one of email or phone must be provided"):
        identify_customer_impl()
