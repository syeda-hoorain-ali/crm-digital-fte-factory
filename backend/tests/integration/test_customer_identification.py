"""Integration tests for customer identification service."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.customer_identification import CustomerIdentificationService
from src.database.models import (
    Customer,
    CustomerIdentifier,
    IdentifierType,
)


class TestCustomerIdentificationService:
    """Test suite for CustomerIdentificationService."""

    @pytest.mark.asyncio
    async def test_find_or_create_customer_by_email_new(self, session: AsyncSession):
        """Test creating new customer by email."""
        service = CustomerIdentificationService(session)

        customer = await service.find_or_create_customer_by_email(
            email="new@example.com",
            name="New Customer",
            metadata={"source": "test"}
        )

        assert customer is not None
        assert customer.email == "new@example.com"
        assert customer.name == "New Customer"
        assert customer.metadata_["source"] == "test"

        # Verify identifier created
        identifiers = await service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 1
        assert identifiers[0].identifier_type == IdentifierType.EMAIL
        assert identifiers[0].identifier_value == "new@example.com"

    @pytest.mark.asyncio
    async def test_find_or_create_customer_by_email_existing(self, session: AsyncSession):
        """Test finding existing customer by email."""
        service = CustomerIdentificationService(session)

        # Create first customer
        customer1 = await service.find_or_create_customer_by_email(
            email="existing@example.com",
            name="First Name"
        )

        # Try to create again with same email
        customer2 = await service.find_or_create_customer_by_email(
            email="existing@example.com",
            name="Second Name"
        )

        # Should return same customer
        assert customer1.id == customer2.id
        assert customer2.email == "existing@example.com"
        # Name should still be first name (not updated)
        assert customer2.name == "First Name"

    @pytest.mark.asyncio
    async def test_find_or_create_customer_by_phone_new(self, session: AsyncSession):
        """Test creating new customer by phone."""
        service = CustomerIdentificationService(session)

        customer = await service.find_or_create_customer_by_phone(
            phone="+1234567890",
            name="Phone Customer",
            metadata={"source": "whatsapp"}
        )

        assert customer is not None
        assert customer.phone == "+1234567890"
        assert customer.name == "Phone Customer"

        # Verify identifier created
        identifiers = await service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 1
        assert identifiers[0].identifier_type == IdentifierType.PHONE
        assert identifiers[0].identifier_value == "+1234567890"

    @pytest.mark.asyncio
    async def test_find_or_create_customer_by_phone_existing(self, session: AsyncSession):
        """Test finding existing customer by phone."""
        service = CustomerIdentificationService(session)

        # Create first customer
        customer1 = await service.find_or_create_customer_by_phone(
            phone="+1234567890",
            name="First Name"
        )

        # Try to create again with same phone
        customer2 = await service.find_or_create_customer_by_phone(
            phone="+1234567890",
            name="Second Name"
        )

        # Should return same customer
        assert customer1.id == customer2.id
        assert customer2.phone == "+1234567890"

    @pytest.mark.asyncio
    async def test_link_email_to_customer(self, session: AsyncSession):
        """Test linking email to existing customer."""
        service = CustomerIdentificationService(session)

        # Create customer with phone
        customer = await service.find_or_create_customer_by_phone(
            phone="+1234567890",
            name="Test Customer"
        )

        # Link email to same customer
        identifier = await service.link_email_to_customer(
            customer_id=customer.id,
            email="test@example.com",
            verified=True
        )

        assert identifier.customer_id == customer.id
        assert identifier.identifier_type == IdentifierType.EMAIL
        assert identifier.identifier_value == "test@example.com"
        assert identifier.verified is True

        # Verify customer now has both identifiers
        identifiers = await service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 2

    @pytest.mark.asyncio
    async def test_link_email_already_linked_to_different_customer(self, session: AsyncSession):
        """Test linking email that's already linked to different customer."""
        service = CustomerIdentificationService(session)

        # Create first customer with email
        customer1 = await service.find_or_create_customer_by_email(
            email="test@example.com"
        )

        # Create second customer with phone
        customer2 = await service.find_or_create_customer_by_phone(
            phone="+1234567890"
        )

        # Try to link same email to second customer
        with pytest.raises(ValueError, match="already linked to a different customer"):
            await service.link_email_to_customer(
                customer_id=customer2.id,
                email="test@example.com"
            )

    @pytest.mark.asyncio
    async def test_link_phone_to_customer(self, session: AsyncSession):
        """Test linking phone to existing customer."""
        service = CustomerIdentificationService(session)

        # Create customer with email
        customer = await service.find_or_create_customer_by_email(
            email="test@example.com",
            name="Test Customer"
        )

        # Link phone to same customer
        identifier = await service.link_phone_to_customer(
            customer_id=customer.id,
            phone="+1234567890",
            verified=False
        )

        assert identifier.customer_id == customer.id
        assert identifier.identifier_type == IdentifierType.PHONE
        assert identifier.identifier_value == "+1234567890"
        assert identifier.verified is False

        # Verify customer now has both identifiers
        identifiers = await service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 2

    @pytest.mark.asyncio
    async def test_find_customer_by_any_identifier_email(self, session: AsyncSession):
        """Test finding customer by email identifier."""
        service = CustomerIdentificationService(session)

        # Create customer
        created_customer = await service.find_or_create_customer_by_email(
            email="find@example.com"
        )

        # Find by email
        found_customer = await service.find_customer_by_any_identifier(
            email="find@example.com"
        )

        assert found_customer is not None
        assert found_customer.id == created_customer.id

    @pytest.mark.asyncio
    async def test_find_customer_by_any_identifier_phone(self, session: AsyncSession):
        """Test finding customer by phone identifier."""
        service = CustomerIdentificationService(session)

        # Create customer
        created_customer = await service.find_or_create_customer_by_phone(
            phone="+1234567890"
        )

        # Find by phone
        found_customer = await service.find_customer_by_any_identifier(
            phone="+1234567890"
        )

        assert found_customer is not None
        assert found_customer.id == created_customer.id

    @pytest.mark.asyncio
    async def test_find_customer_by_any_identifier_both(self, session: AsyncSession):
        """Test finding customer with both email and phone."""
        service = CustomerIdentificationService(session)

        # Create customer with email
        customer = await service.find_or_create_customer_by_email(
            email="both@example.com"
        )

        # Link phone
        await service.link_phone_to_customer(
            customer_id=customer.id,
            phone="+1234567890"
        )

        # Find by email
        found1 = await service.find_customer_by_any_identifier(
            email="both@example.com"
        )
        assert found1
        assert found1.id == customer.id

        # Find by phone
        found2 = await service.find_customer_by_any_identifier(
            phone="+1234567890"
        )
        assert found2
        assert found2.id == customer.id

        # Find by both (should prefer email)
        found3 = await service.find_customer_by_any_identifier(
            email="both@example.com",
            phone="+1234567890"
        )
        assert found3
        assert found3.id == customer.id

    @pytest.mark.asyncio
    async def test_find_customer_by_any_identifier_not_found(self, session: AsyncSession):
        """Test finding non-existent customer."""
        service = CustomerIdentificationService(session)

        found = await service.find_customer_by_any_identifier(
            email="nonexistent@example.com"
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_merge_customers(self, session: AsyncSession):
        """Test merging two customer records."""
        service = CustomerIdentificationService(session)

        # Create two customers
        customer1 = await service.find_or_create_customer_by_email(
            email="primary@example.com",
            name="Primary Customer"
        )

        customer2 = await service.find_or_create_customer_by_phone(
            phone="+1234567890",
            name="Secondary Customer"
        )

        # Merge customer2 into customer1
        merged = await service.merge_customers(
            primary_customer_id=customer1.id,
            secondary_customer_id=customer2.id
        )

        assert merged.id == customer1.id

        # Verify primary customer now has both identifiers
        identifiers = await service.get_customer_identifiers(customer1.id)
        assert len(identifiers) == 2

        identifier_types = {id.identifier_type for id in identifiers}
        assert IdentifierType.EMAIL in identifier_types
        assert IdentifierType.PHONE in identifier_types

    @pytest.mark.asyncio
    async def test_merge_customers_same_customer(self, session: AsyncSession):
        """Test merging customer with itself fails."""
        service = CustomerIdentificationService(session)

        customer = await service.find_or_create_customer_by_email(
            email="test@example.com"
        )

        with pytest.raises(ValueError, match="Cannot merge customer with itself"):
            await service.merge_customers(
                primary_customer_id=customer.id,
                secondary_customer_id=customer.id
            )

    @pytest.mark.asyncio
    async def test_merge_customers_duplicate_identifiers(self, session: AsyncSession):
        """Test merging customers with duplicate identifiers."""
        service = CustomerIdentificationService(session)

        # Create two customers with same email (shouldn't happen but test handling)
        customer1 = Customer(
            email="duplicate@example.com",
            name="Customer 1"
        )
        session.add(customer1)
        await session.commit()
        await session.refresh(customer1)

        identifier1 = CustomerIdentifier(
            customer_id=customer1.id,
            identifier_type=IdentifierType.EMAIL,
            identifier_value="duplicate@example.com"
        )
        session.add(identifier1)

        customer2 = Customer(
            email="duplicate@example.com",
            name="Customer 2"
        )
        session.add(customer2)
        await session.commit()
        await session.refresh(customer2)

        identifier2 = CustomerIdentifier(
            customer_id=customer2.id,
            identifier_type=IdentifierType.EMAIL,
            identifier_value="duplicate@example.com"
        )
        session.add(identifier2)
        await session.commit()

        # Merge should handle duplicate by keeping primary's identifier
        merged = await service.merge_customers(
            primary_customer_id=customer1.id,
            secondary_customer_id=customer2.id
        )

        # Should only have one email identifier now
        identifiers = await service.get_customer_identifiers(customer1.id)
        email_identifiers = [
            id for id in identifiers
            if id.identifier_type == IdentifierType.EMAIL
        ]
        assert len(email_identifiers) == 1

    @pytest.mark.asyncio
    async def test_get_customer_identifiers_empty(self, session: AsyncSession):
        """Test getting identifiers for customer with none."""
        service = CustomerIdentificationService(session)

        # Create customer without using service (no identifiers)
        customer = Customer(name="No Identifiers")
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

        identifiers = await service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 0

    @pytest.mark.asyncio
    async def test_link_email_idempotent(self, session: AsyncSession):
        """Test linking same email twice is idempotent."""
        service = CustomerIdentificationService(session)

        customer = await service.find_or_create_customer_by_email(
            email="test@example.com"
        )

        # Link same email again
        identifier = await service.link_email_to_customer(
            customer_id=customer.id,
            email="test@example.com"
        )

        # Should return existing identifier
        assert identifier.customer_id == customer.id

        # Should still only have one identifier
        identifiers = await service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 1
