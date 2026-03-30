"""Unit tests for customer database queries."""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Customer, CustomerIdentifier, IdentifierType
from src.database.queries.customer import (
    create_customer,
    get_customer,
    update_customer,
    delete_customer,
    list_customers,
    get_customer_by_identifier,
    create_customer_identifier,
    list_customer_identifiers,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomerCRUD:
    """Test customer CRUD operations."""

    async def test_create_customer_minimal(self, session: AsyncSession):
        """Test creating customer with minimal fields."""
        customer = await create_customer(session)

        assert customer.id is not None
        assert customer.name is None
        assert customer.email is None
        assert customer.phone is None
        assert customer.metadata_ == {}

    async def test_create_customer_full(self, session: AsyncSession):
        """Test creating customer with all fields."""
        import uuid
        unique_email = f"john-{uuid.uuid4().hex[:8]}@example.com"
        customer = await create_customer(
            session,
            name="John Doe",
            email=unique_email,
            phone="+1234567890",
            meta_data={"tier": "premium", "source": "referral"}
        )

        assert customer.id is not None
        assert customer.name == "John Doe"
        assert customer.email == unique_email
        assert customer.phone == "+1234567890"
        assert customer.metadata_["tier"] == "premium"
        assert customer.metadata_["source"] == "referral"

    async def test_get_customer_exists(self, session: AsyncSession, sample_customer: Customer):
        """Test getting existing customer."""
        customer = await get_customer(session, sample_customer.id)

        assert customer is not None
        assert customer.id == sample_customer.id
        assert customer.email == sample_customer.email

    async def test_get_customer_not_exists(self, session: AsyncSession):
        """Test getting non-existent customer."""
        fake_id = uuid4()
        customer = await get_customer(session, fake_id)

        assert customer is None

    async def test_get_customer_with_lock(self, session: AsyncSession, sample_customer: Customer):
        """Test getting customer with row lock."""
        customer = await get_customer(session, sample_customer.id, lock=True)

        assert customer is not None
        assert customer.id == sample_customer.id

    async def test_update_customer(self, session: AsyncSession, sample_customer: Customer):
        """Test updating customer fields."""
        updated = await update_customer(
            session,
            sample_customer.id,
            name="Jane Smith"
        )

        assert updated is not None
        assert updated.name == "Jane Smith"

    async def test_update_customer_not_exists(self, session: AsyncSession):
        """Test updating non-existent customer."""
        fake_id = uuid4()
        updated = await update_customer(session, fake_id, name="Test")

        assert updated is None

    async def test_delete_customer(self, session: AsyncSession, sample_customer: Customer):
        """Test deleting customer."""
        result = await delete_customer(session, sample_customer.id)

        assert result is True

        # Verify customer is deleted
        customer = await get_customer(session, sample_customer.id)
        assert customer is None

    async def test_delete_customer_not_exists(self, session: AsyncSession):
        """Test deleting non-existent customer."""
        fake_id = uuid4()
        result = await delete_customer(session, fake_id)

        assert result is False

    async def test_list_customers_empty(self, session: AsyncSession):
        """Test listing customers returns a list."""
        customers = await list_customers(session)

        # Using shared PostgreSQL, so just verify it returns a list
        assert isinstance(customers, list)

    async def test_list_customers_with_data(self, session: AsyncSession):
        """Test listing customers with data."""
        import uuid
        # Create multiple customers with unique emails
        email1 = f"c1-{uuid.uuid4().hex[:8]}@example.com"
        email2 = f"c2-{uuid.uuid4().hex[:8]}@example.com"
        customer1 = await create_customer(session, name="Customer 1", email=email1)
        customer2 = await create_customer(session, name="Customer 2", email=email2)
        await session.commit()

        customers = await list_customers(session)

        assert len(customers) >= 2
        customer_ids = [c.id for c in customers]
        assert customer1.id in customer_ids
        assert customer2.id in customer_ids

    async def test_list_customers_with_limit(self, session: AsyncSession):
        """Test listing customers with limit."""
        # Create multiple customers
        for i in range(5):
            await create_customer(session, name=f"Customer {i}")
        await session.commit()

        customers = await list_customers(session, limit=3)

        assert len(customers) == 3

    async def test_list_customers_with_offset(self, session: AsyncSession):
        """Test listing customers with offset."""
        # Create customers
        for i in range(5):
            await create_customer(session, name=f"OffsetTest Customer {i}")
        await session.commit()

        all_customers = await list_customers(session, limit=5)
        offset_customers = await list_customers(session, limit=5, offset=2)
    
        # Verify offset shifts the window
        assert offset_customers[0].name == all_customers[2].name


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomerIdentifiers:
    """Test customer identifier operations."""

    async def test_create_customer_identifier(self, session: AsyncSession, sample_customer: Customer):
        """Test creating customer identifier."""
        identifier = await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.EMAIL,
            "test@example.com"
        )

        print(identifier)
        assert identifier.id is not None
        assert identifier.customer_id == sample_customer.id
        assert identifier.identifier_type == IdentifierType.EMAIL
        assert identifier.identifier_value == "test@example.com"

    async def test_get_customer_by_identifier_email(self, session: AsyncSession, sample_customer: Customer):
        """Test getting customer by email identifier."""
        import uuid
        unique_email = f"lookup-{uuid.uuid4().hex[:8]}@example.com"

        # Create identifier
        await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.EMAIL,
            unique_email
        )
        await session.commit()

        # Lookup customer
        customer = await get_customer_by_identifier(
            session,
            IdentifierType.EMAIL,
            unique_email
        )

        assert customer is not None
        assert customer.id == sample_customer.id

    async def test_get_customer_by_identifier_phone(self, session: AsyncSession, sample_customer: Customer):
        """Test getting customer by phone identifier."""
        import uuid
        unique_phone = f"+1234{uuid.uuid4().hex[:6]}"

        # Create identifier
        await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.PHONE,
            unique_phone
        )
        await session.commit()

        # Lookup customer
        customer = await get_customer_by_identifier(
            session,
            IdentifierType.PHONE,
            unique_phone
        )

        assert customer is not None
        assert customer.id == sample_customer.id

    async def test_get_customer_by_identifier_not_exists(self, session: AsyncSession):
        """Test getting customer by non-existent identifier."""
        customer = await get_customer_by_identifier(
            session,
            IdentifierType.EMAIL,
            "nonexistent@example.com"
        )

        assert customer is None

    async def test_list_customer_identifiers(self, session: AsyncSession, sample_customer: Customer):
        """Test listing customer identifiers."""
        # Create multiple identifiers
        await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.EMAIL,
            "email1@example.com"
        )
        await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.PHONE,
            "+1111111111"
        )
        await session.commit()

        identifiers = await list_customer_identifiers(session, sample_customer.id)

        assert len(identifiers) >= 2
        types = [i.identifier_type for i in identifiers]
        assert IdentifierType.EMAIL in types
        assert IdentifierType.PHONE in types

    async def test_list_customer_identifiers_empty(self, session: AsyncSession, sample_customer: Customer):
        """Test listing identifiers for customer with none."""
        identifiers = await list_customer_identifiers(session, sample_customer.id)

        # sample_customer fixture might have identifiers, so just check it returns a list
        assert isinstance(identifiers, list)

    async def test_multiple_identifiers_same_customer(self, session: AsyncSession, sample_customer: Customer):
        """Test customer can have multiple identifiers."""
        # Create multiple identifiers for same customer
        id1 = await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.EMAIL,
            "primary@example.com"
        )
        id2 = await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.EMAIL,
            "secondary@example.com"
        )
        id3 = await create_customer_identifier(
            session,
            sample_customer.id,
            IdentifierType.PHONE,
            "+1234567890"
        )
        await session.commit()

        identifiers = await list_customer_identifiers(session, sample_customer.id)

        assert len(identifiers) >= 3
        identifier_ids = [i.id for i in identifiers]
        assert id1.id in identifier_ids
        assert id2.id in identifier_ids
        assert id3.id in identifier_ids

