"""Customer identification service for cross-channel recognition."""

import logging
from typing import Optional
from uuid import UUID

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import (
    Customer,
    CustomerIdentifier,
    IdentifierType,
)

logger = logging.getLogger(__name__)


class CustomerIdentificationService:
    """Service for identifying and linking customers across channels."""

    def __init__(self, session: AsyncSession):
        """Initialize customer identification service.

        Args:
            session: Database session
        """
        self.session = session

    async def find_or_create_customer_by_email(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Customer:
        """Find existing customer by email or create new one.

        Args:
            email: Customer email address
            name: Optional customer name
            metadata: Optional metadata dictionary

        Returns:
            Customer record (existing or newly created)
        """
        # Look for existing customer identifier
        result = await self.session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.identifier_type == IdentifierType.EMAIL)
            .where(CustomerIdentifier.identifier_value == email)
        )
        identifier = result.scalars().first()

        if identifier:
            # Found existing identifier - get customer
            customer = await self.session.get(Customer, identifier.customer_id)
            if customer:
                logger.info(
                    f"Found existing customer by email",
                    extra={
                        "customer_id": str(customer.id),
                        "email": email
                    }
                )
                # Update name if provided and not set
                if name and not customer.name:
                    customer.name = name
                    self.session.add(customer)
                    await self.session.commit()
                    await self.session.refresh(customer)
                return customer

        # No existing customer - create new one
        customer = Customer(
            email=email,
            name=name,
            metadata_=metadata or {}
        )
        self.session.add(customer)
        await self.session.commit()
        await self.session.refresh(customer)

        # Create email identifier
        email_identifier = CustomerIdentifier(
            customer_id=customer.id,
            identifier_type=IdentifierType.EMAIL,
            identifier_value=email,
            verified=False
        )
        self.session.add(email_identifier)
        await self.session.commit()

        logger.info(
            f"Created new customer with email identifier",
            extra={
                "customer_id": str(customer.id),
                "email": email
            }
        )

        return customer

    async def find_or_create_customer_by_phone(
        self,
        phone: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Customer:
        """Find existing customer by phone or create new one.

        Args:
            phone: Customer phone number
            name: Optional customer name
            metadata: Optional metadata dictionary

        Returns:
            Customer record (existing or newly created)
        """
        # Look for existing customer identifier
        result = await self.session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.identifier_type == IdentifierType.PHONE)
            .where(CustomerIdentifier.identifier_value == phone)
        )
        identifier = result.scalars().first()

        if identifier:
            # Found existing identifier - get customer
            customer = await self.session.get(Customer, identifier.customer_id)
            if customer:
                logger.info(
                    f"Found existing customer by phone",
                    extra={
                        "customer_id": str(customer.id),
                        "phone": phone
                    }
                )
                # Update name if provided and not set
                if name and not customer.name:
                    customer.name = name
                    self.session.add(customer)
                    await self.session.commit()
                    await self.session.refresh(customer)
                return customer

        # No existing customer - create new one
        customer = Customer(
            phone=phone,
            name=name,
            metadata_=metadata or {}
        )
        self.session.add(customer)
        await self.session.commit()
        await self.session.refresh(customer)

        # Create phone identifier
        phone_identifier = CustomerIdentifier(
            customer_id=customer.id,
            identifier_type=IdentifierType.PHONE,
            identifier_value=phone,
            verified=False
        )
        self.session.add(phone_identifier)
        await self.session.commit()

        logger.info(
            f"Created new customer with phone identifier",
            extra={
                "customer_id": str(customer.id),
                "phone": phone
            }
        )

        return customer

    async def link_email_to_customer(
        self,
        customer_id: UUID,
        email: str,
        verified: bool = False
    ) -> CustomerIdentifier:
        """Link an email address to an existing customer.

        Args:
            customer_id: Customer UUID
            email: Email address to link
            verified: Whether the email is verified

        Returns:
            CustomerIdentifier record

        Raises:
            ValueError: If email already linked to different customer
        """
        # Check if email already exists
        result = await self.session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.identifier_type == IdentifierType.EMAIL)
            .where(CustomerIdentifier.identifier_value == email)
        )
        existing = result.scalars().first()

        if existing:
            if existing.customer_id == customer_id:
                # Already linked to this customer
                logger.info(
                    f"Email already linked to customer",
                    extra={
                        "customer_id": str(customer_id),
                        "email": email
                    }
                )
                return existing
            else:
                # Linked to different customer
                logger.warning(
                    f"Email already linked to different customer",
                    extra={
                        "customer_id": str(customer_id),
                        "existing_customer_id": str(existing.customer_id),
                        "email": email
                    }
                )
                raise ValueError(
                    f"Email {email} is already linked to a different customer"
                )

        # Create new identifier
        identifier = CustomerIdentifier(
            customer_id=customer_id,
            identifier_type=IdentifierType.EMAIL,
            identifier_value=email,
            verified=verified
        )
        self.session.add(identifier)
        await self.session.commit()
        await self.session.refresh(identifier)

        logger.info(
            f"Linked email to customer",
            extra={
                "customer_id": str(customer_id),
                "email": email,
                "verified": verified
            }
        )

        return identifier

    async def link_phone_to_customer(
        self,
        customer_id: UUID,
        phone: str,
        verified: bool = False
    ) -> CustomerIdentifier:
        """Link a phone number to an existing customer.

        Args:
            customer_id: Customer UUID
            phone: Phone number to link
            verified: Whether the phone is verified

        Returns:
            CustomerIdentifier record

        Raises:
            ValueError: If phone already linked to different customer
        """
        # Check if phone already exists
        result = await self.session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.identifier_type == IdentifierType.PHONE)
            .where(CustomerIdentifier.identifier_value == phone)
        )
        existing = result.scalars().first()

        if existing:
            if existing.customer_id == customer_id:
                # Already linked to this customer
                logger.info(
                    f"Phone already linked to customer",
                    extra={
                        "customer_id": str(customer_id),
                        "phone": phone
                    }
                )
                return existing
            else:
                # Linked to different customer
                logger.warning(
                    f"Phone already linked to different customer",
                    extra={
                        "customer_id": str(customer_id),
                        "existing_customer_id": str(existing.customer_id),
                        "phone": phone
                    }
                )
                raise ValueError(
                    f"Phone {phone} is already linked to a different customer"
                )

        # Create new identifier
        identifier = CustomerIdentifier(
            customer_id=customer_id,
            identifier_type=IdentifierType.PHONE,
            identifier_value=phone,
            verified=verified
        )
        self.session.add(identifier)

        # Also update the Customer.phone field if not already set
        customer = await self.session.get(Customer, customer_id)
        if customer and not customer.phone:
            customer.phone = phone
            self.session.add(customer)

        await self.session.commit()
        await self.session.refresh(identifier)

        logger.info(
            f"Linked phone to customer",
            extra={
                "customer_id": str(customer_id),
                "phone": phone,
                "verified": verified
            }
        )

        return identifier

    async def get_customer_identifiers(
        self,
        customer_id: UUID
    ) -> list[CustomerIdentifier]:
        """Get all identifiers for a customer.

        Args:
            customer_id: Customer UUID

        Returns:
            List of CustomerIdentifier records
        """
        result = await self.session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.customer_id == customer_id)
        )
        return list(result.scalars().all())

    async def find_customer_by_any_identifier(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Optional[Customer]:
        """Find customer by any available identifier.

        Tries email first, then phone. Returns first match found.

        Args:
            email: Optional email address
            phone: Optional phone number

        Returns:
            Customer record if found, None otherwise
        """
        # Try email first
        if email:
            result = await self.session.execute(
                select(CustomerIdentifier)
                .where(CustomerIdentifier.identifier_type == IdentifierType.EMAIL)
                .where(CustomerIdentifier.identifier_value == email)
            )
            identifier = result.scalars().first()
            if identifier:
                customer = await self.session.get(Customer, identifier.customer_id)
                if customer:
                    return customer

        # Try phone
        if phone:
            result = await self.session.execute(
                select(CustomerIdentifier)
                .where(CustomerIdentifier.identifier_type == IdentifierType.PHONE)
                .where(CustomerIdentifier.identifier_value == phone)
            )
            identifier = result.scalars().first()
            if identifier:
                customer = await self.session.get(Customer, identifier.customer_id)
                if customer:
                    return customer

        return None

    async def merge_customers(
        self,
        primary_customer_id: UUID,
        secondary_customer_id: UUID
    ) -> Customer:
        """Merge two customer records (manual operation).

        Moves all identifiers from secondary to primary customer.
        Does NOT move conversations or messages - that should be done separately.

        Args:
            primary_customer_id: Customer to keep
            secondary_customer_id: Customer to merge into primary

        Returns:
            Primary customer record

        Raises:
            ValueError: If customers don't exist or are the same
        """
        if primary_customer_id == secondary_customer_id:
            raise ValueError("Cannot merge customer with itself")

        # Get both customers
        primary = await self.session.get(Customer, primary_customer_id)
        secondary = await self.session.get(Customer, secondary_customer_id)

        if not primary or not secondary:
            raise ValueError("One or both customers not found")

        # Move all identifiers from secondary to primary
        result = await self.session.execute(
            select(CustomerIdentifier)
            .where(CustomerIdentifier.customer_id == secondary_customer_id)
        )
        identifiers = result.all()

        for identifier in identifiers:
            # Check if primary already has this identifier type/value
            existing = await self.session.execute(
                select(CustomerIdentifier)
                .where(CustomerIdentifier.customer_id == primary_customer_id)
                .where(CustomerIdentifier.identifier_type == identifier.identifier_type)
                .where(CustomerIdentifier.identifier_value == identifier.identifier_value)
            )
            if existing.first():
                # Primary already has this identifier - delete duplicate
                await self.session.delete(identifier)
            else:
                # Move to primary
                identifier.customer_id = primary_customer_id
                self.session.add(identifier)

        await self.session.commit()

        logger.info(
            f"Merged customers",
            extra={
                "primary_customer_id": str(primary_customer_id),
                "secondary_customer_id": str(secondary_customer_id),
                "identifiers_moved": len(identifiers)
            }
        )

        return primary
