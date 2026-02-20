"""Identify or create customer tool implementation."""
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from src.database.models import Customer
from src.database.session import engine
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit


def identify_customer_impl(email: Optional[str] = None, phone: Optional[str] = None, client_id: str = "default_client") -> Dict[str, Any]:
    """
    Implementation for identifying or creating a customer based on email or phone.

    Args:
        email: Customer's email address (optional)
        phone: Customer's phone number (optional)
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        Dictionary containing:
        - customer_id: UUID of the customer
        - is_new: Boolean indicating if this is a newly created customer
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("identify_customer")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("identify_customer", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Normalize inputs first - strip whitespace and convert empty strings to None
        email = email.strip() if email else None
        email = email if email else None  # Convert empty string to None after strip
        phone = phone.strip() if phone else None
        phone = phone if phone else None  # Convert empty string to None after strip

        # Input validation - at least one identifier must be provided
        if not email and not phone:
            raise ValueError("At least one of email or phone must be provided")

        with Session(engine) as session:
            # Try to find existing customer by email or phone
            customer = None

            if email and phone:
                # Search by both email and phone (OR condition)
                customer_statement = select(Customer).where(
                    (Customer.email == email) | (Customer.phone == phone)
                )
                customer = session.exec(customer_statement).first()
            elif email:
                # Search by email only
                customer_statement = select(Customer).where(Customer.email == email)
                customer = session.exec(customer_statement).first()
            elif phone:
                # Search by phone only
                customer_statement = select(Customer).where(Customer.phone == phone)
                customer = session.exec(customer_statement).first()

            if customer:
                # Customer exists - return existing ID
                duration = time.time() - start_time
                metrics_collector.record_response_time("identify_customer", duration)
                return {
                    "customer_id": customer.customer_id,
                    "is_new": False
                }
            else:
                # Customer doesn't exist - create new record
                new_customer_id = str(uuid.uuid4())

                new_customer = Customer(
                    customer_id=new_customer_id,
                    email=email,
                    phone=phone,
                    plan_type="unknown",
                    subscription_status="active",
                    last_interaction=datetime.now()
                )

                try:
                    session.add(new_customer)
                    session.commit()
                    session.refresh(new_customer)

                    duration = time.time() - start_time
                    metrics_collector.record_response_time("identify_customer", duration)
                    return {
                        "customer_id": new_customer.customer_id,
                        "is_new": True
                    }
                except IntegrityError as db_error:
                    # Handle unique constraint violations gracefully
                    session.rollback()

                    # Try to fetch the customer again (race condition scenario)
                    if email and phone:
                        customer_statement = select(Customer).where(
                            (Customer.email == email) | (Customer.phone == phone)
                        )
                    elif email:
                        customer_statement = select(Customer).where(Customer.email == email)
                    else:
                        customer_statement = select(Customer).where(Customer.phone == phone)

                    customer = session.exec(customer_statement).first()

                    if customer:
                        # Another process created the customer
                        duration = time.time() - start_time
                        metrics_collector.record_response_time("identify_customer", duration)
                        return {
                            "customer_id": customer.customer_id,
                            "is_new": False
                        }
                    else:
                        # Unexpected database error
                        raise db_error

    except ValueError as ve:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("identify_customer", duration)
        raise ve
    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("identify_customer", duration)
        raise e
