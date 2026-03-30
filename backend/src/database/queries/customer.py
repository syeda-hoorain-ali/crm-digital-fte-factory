"""Customer and CustomerIdentifier CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlmodel import col
from sqlalchemy import select, delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from ..models import (
    Customer,
    CustomerIdentifier,
    IdentifierType,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Customer CRUD Operations (T020)
# ============================================================================

async def create_customer(
    session: AsyncSession,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    meta_data: dict | None = None,
) -> Customer:
    """
    Create a new customer.

    Args:
        session: Database session
        name: Customer name (optional)
        email: Customer email (optional)
        phone: Customer phone (optional)
        meta_data: Customer metadata (optional)

    Returns:
        Customer: Created customer instance
    """
    import time
    start_time = time.time()

    try:
        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            metadata_=meta_data or {},
        )
        session.add(customer)
        await session.flush()
        await session.refresh(customer)

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Created customer",
            extra={
                "operation": "create",
                "entity": "customer",
                "customer_id": str(customer.id),
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return customer
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to create customer: {e}",
            extra={
                "operation": "create",
                "entity": "customer",
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise


async def get_customer(
    session: AsyncSession,
    customer_id: UUID,
    lock: bool = False,
) -> Customer | None:
    """
    Get customer by ID with optional row-level locking (T016).

    Args:
        session: Database session
        customer_id: Customer UUID
        lock: If True, acquire FOR UPDATE lock for concurrent updates

    Returns:
        Customer | None: Customer instance or None if not found
    """
    import time
    start_time = time.time()

    try:
        stmt = select(Customer).where(col(Customer.id) == customer_id)

        if lock:
            # Row-level locking for concurrent customer record updates (T016)
            stmt = stmt.with_for_update()

        result = await session.execute(stmt)
        customer = result.scalar_one_or_none()

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Retrieved customer",
            extra={
                "operation": "get",
                "entity": "customer",
                "customer_id": str(customer_id),
                "found": customer is not None,
                "locked": lock,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return customer
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to get customer: {e}",
            extra={
                "operation": "get",
                "entity": "customer",
                "customer_id": str(customer_id),
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise


async def update_customer(
    session: AsyncSession,
    customer_id: UUID,
    name: str | None = None,
) -> Customer | None:
    """
    Update customer with row-level locking (T016).

    Args:
        session: Database session
        customer_id: Customer UUID
        name: New customer name (optional)

    Returns:
        Customer | None: Updated customer or None if not found
    """
    # Acquire row-level lock for concurrent updates (T016)
    customer = await get_customer(session, customer_id, lock=True)

    if not customer:
        return None

    if name is not None:
        customer.name = name

    customer.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(customer)
    return customer


async def delete_customer(
    session: AsyncSession,
    customer_id: UUID,
) -> bool:
    """
    Delete customer by ID.

    Args:
        session: Database session
        customer_id: Customer UUID

    Returns:
        bool: True if deleted, False if not found
    """
    stmt = delete(Customer).where(col(Customer.id) == customer_id)
    result = cast(CursorResult, await session.execute(stmt))
    return result.rowcount > 0


async def list_customers(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
) -> List[Customer]:
    """
    List customers with pagination.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List[Customer]: List of customers
    """
    stmt = (
        select(Customer)
        .order_by(col(Customer.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# CustomerIdentifier CRUD Operations (T021)
# ============================================================================

async def create_customer_identifier(
    session: AsyncSession,
    customer_id: UUID,
    identifier_type: IdentifierType,
    identifier_value: str,
) -> CustomerIdentifier:
    """
    Create a new customer identifier for cross-channel matching.

    Args:
        session: Database session
        customer_id: Customer UUID
        identifier_type: Type of identifier (email, phone, etc.)
        identifier_value: Identifier value

    Returns:
        CustomerIdentifier: Created identifier instance
    """
    identifier = CustomerIdentifier(
        customer_id=customer_id,
        identifier_type=identifier_type,
        identifier_value=identifier_value,
    )
    session.add(identifier)
    await session.flush()
    await session.refresh(identifier)
    return identifier


async def get_customer_by_identifier(
    session: AsyncSession,
    identifier_type: IdentifierType,
    identifier_value: str,
) -> Customer | None:
    """
    Cross-channel customer lookup by identifier (T021).

    Args:
        session: Database session
        identifier_type: Type of identifier
        identifier_value: Identifier value

    Returns:
        Customer | None: Customer instance or None if not found
    """
    stmt = (
        select(Customer)
        .join(CustomerIdentifier)
        .where(
            col(CustomerIdentifier.identifier_type) == identifier_type,
            col(CustomerIdentifier.identifier_value) == identifier_value,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_customer_identifiers(
    session: AsyncSession,
    customer_id: UUID,
) -> List[CustomerIdentifier]:
    """
    List all identifiers for a customer.

    Args:
        session: Database session
        customer_id: Customer UUID

    Returns:
        List[CustomerIdentifier]: List of identifiers
    """
    stmt = select(CustomerIdentifier).where(
        col(CustomerIdentifier.customer_id) == customer_id
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def identify_or_create_customer(
    session: AsyncSession,
    email: str | None = None,
    phone: str | None = None,
    name: str | None = None,
) -> Customer:
    """
    Identify existing customer or create new one based on email/phone.

    This function implements the customer identification logic:
    1. Try to find customer by email (if provided)
    2. Try to find customer by phone (if provided)
    3. If not found, create new customer with provided contact info

    Args:
        session: Database session
        email: Customer email (optional)
        phone: Customer phone (optional)
        name: Customer name (optional, used only for new customers)

    Returns:
        Customer: Existing or newly created customer instance

    Raises:
        ValueError: If neither email nor phone is provided
    """
    import time
    start_time = time.time()

    if not email and not phone:
        raise ValueError("At least one of email or phone must be provided")

    try:
        # Try to find existing customer by email
        if email:
            customer = await get_customer_by_identifier(
                session,
                IdentifierType.EMAIL,
                email,
            )
            if customer:
                execution_time = (time.time() - start_time) * 1000
                logger.info(
                    f"Customer identified by email",
                    extra={
                        "operation": "identify",
                        "entity": "customer",
                        "customer_id": str(customer.id),
                        "identifier_type": "email",
                        "execution_time_ms": round(execution_time, 2),
                        "success": True,
                    }
                )
                return customer

        # Try to find existing customer by phone
        if phone:
            customer = await get_customer_by_identifier(
                session,
                IdentifierType.PHONE,
                phone,
            )
            if customer:
                execution_time = (time.time() - start_time) * 1000
                logger.info(
                    f"Customer identified by phone",
                    extra={
                        "operation": "identify",
                        "entity": "customer",
                        "customer_id": str(customer.id),
                        "identifier_type": "phone",
                        "execution_time_ms": round(execution_time, 2),
                        "success": True,
                    }
                )
                return customer

        # Customer not found - create new one
        customer = await create_customer(
            session=session,
            name=name,
            email=email,
            phone=phone,
        )

        # Create identifiers for cross-channel matching
        if email:
            await create_customer_identifier(
                session=session,
                customer_id=customer.id,
                identifier_type=IdentifierType.EMAIL,
                identifier_value=email,
            )

        if phone:
            await create_customer_identifier(
                session=session,
                customer_id=customer.id,
                identifier_type=IdentifierType.PHONE,
                identifier_value=phone,
            )

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"New customer created",
            extra={
                "operation": "create",
                "entity": "customer",
                "customer_id": str(customer.id),
                "has_email": email is not None,
                "has_phone": phone is not None,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return customer

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to identify or create customer: {e}",
            extra={
                "operation": "identify_or_create",
                "entity": "customer",
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise
