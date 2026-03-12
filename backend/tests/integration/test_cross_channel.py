"""Integration tests for cross-channel customer linking."""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.customer_identification import CustomerIdentificationService
from src.services.conversation_service import ConversationService
from src.database.models import (
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Channel,
    IdentifierType,
    ConversationStatus,
    MessageDirection,
    MessageRole,
    DeliveryStatus,
)


class TestCrossChannelLinking:
    """Test suite for cross-channel customer linking."""

    @pytest.mark.asyncio
    async def test_customer_recognized_across_email_and_webform(self, session: AsyncSession):
        """Test customer recognized when using email on both channels."""
        identification_service = CustomerIdentificationService(session)

        # Customer submits web form
        customer1 = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com",
            name="John Doe",
            metadata={"source": "webform"}
        )

        # Same customer sends email
        customer2 = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com",
            name="John Doe"
        )

        # Should be same customer
        assert customer1.id == customer2.id

        # Should have one email identifier
        identifiers = await identification_service.get_customer_identifiers(customer1.id)
        assert len(identifiers) == 1
        assert identifiers[0].identifier_type == IdentifierType.EMAIL

    @pytest.mark.asyncio
    async def test_customer_linked_email_and_phone(self, session: AsyncSession):
        """Test linking customer who provides both email and phone."""
        identification_service = CustomerIdentificationService(session)

        # Customer submits web form with email
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com",
            name="John Doe"
        )

        # Same customer messages via WhatsApp (phone)
        await identification_service.link_phone_to_customer(
            customer_id=customer.id,
            phone="+1234567890"
        )

        # Verify customer has both identifiers
        identifiers = await identification_service.get_customer_identifiers(customer.id)
        assert len(identifiers) == 2

        identifier_types = {id.identifier_type for id in identifiers}
        assert IdentifierType.EMAIL in identifier_types
        assert IdentifierType.PHONE in identifier_types

        # Should be able to find customer by either identifier
        found_by_email = await identification_service.find_customer_by_any_identifier(
            email="customer@example.com"
        )
        found_by_phone = await identification_service.find_customer_by_any_identifier(
            phone="+1234567890"
        )

        assert found_by_email
        assert found_by_email.id == customer.id
        assert found_by_phone
        assert found_by_phone.id == customer.id

    @pytest.mark.asyncio
    async def test_conversation_continuity_across_channels(self, session: AsyncSession):
        """Test detecting conversation continuity when customer switches channels."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com",
            name="John Doe"
        )

        # Customer starts conversation via email about billing
        email_conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(email_conversation)
        await session.commit()
        await session.refresh(email_conversation)

        # Add message about billing
        email_message = Message(
            conversation_id=email_conversation.id,
            channel=Channel.EMAIL,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content="I have a question about my billing statement and invoice charges",
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(email_message)
        await session.commit()

        # Customer switches to web form with similar issue
        new_message_content = "Need help with invoice and billing charges on my account"

        # Detect continuity
        related_conversation = await conversation_service.detect_conversation_continuity(
            customer_id=customer.id,
            new_message_content=new_message_content,
            new_channel=Channel.WEB_FORM,
            similarity_threshold=0.3
        )

        # Should detect the email conversation as related
        assert related_conversation is not None
        assert related_conversation.id == email_conversation.id

    @pytest.mark.asyncio
    async def test_conversation_continuity_not_detected_different_topic(self, session: AsyncSession):
        """Test conversation continuity not detected for different topics."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com"
        )

        # Customer has conversation about billing
        old_conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(old_conversation)
        await session.commit()
        await session.refresh(old_conversation)

        old_message = Message(
            conversation_id=old_conversation.id,
            channel=Channel.EMAIL,
            direction=MessageDirection.INBOUND,
            role=MessageRole.CUSTOMER,
            content="I have a question about my billing statement",
            delivery_status=DeliveryStatus.DELIVERED
        )
        session.add(old_message)
        await session.commit()

        # Customer asks about completely different topic
        new_message_content = "How do I reset my password for the portal?"

        # Should not detect continuity
        related_conversation = await conversation_service.detect_conversation_continuity(
            customer_id=customer.id,
            new_message_content=new_message_content,
            new_channel=Channel.WEB_FORM,
            similarity_threshold=0.3
        )

        assert related_conversation is None

    @pytest.mark.asyncio
    async def test_unified_customer_history_multiple_channels(self, session: AsyncSession):
        """Test unified customer history across multiple channels."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com",
            name="John Doe"
        )

        # Create conversations on different channels
        channels = [Channel.EMAIL, Channel.WEB_FORM, Channel.WHATSAPP]
        conversations = []

        for channel in channels:
            conversation = Conversation(
                customer_id=customer.id,
                initial_channel=channel,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            conversations.append(conversation)

            # Add a message to each conversation
            message = Message(
                conversation_id=conversation.id,
                channel=channel,
                direction=MessageDirection.INBOUND,
                role=MessageRole.CUSTOMER,
                content=f"Message from {channel.value}",
                delivery_status=DeliveryStatus.DELIVERED
            )
            session.add(message)

        await session.commit()

        # Get unified history
        history = await conversation_service.get_customer_conversation_history(
            customer_id=customer.id
        )

        # Should have all three conversations
        assert len(history) == 3

        # Should have all three channels represented
        channels_in_history = {conv['channel'] for conv in history}
        assert 'email' in channels_in_history
        assert 'webform' in channels_in_history
        assert 'whatsapp' in channels_in_history

        # Each conversation should have at least one message
        for conv in history:
            assert conv['message_count'] >= 1
            assert len(conv['messages']) >= 1

    @pytest.mark.asyncio
    async def test_active_conversation_detection(self, session: AsyncSession):
        """Test finding active conversation for customer."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com"
        )

        # Create active conversation
        active_conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(active_conversation)
        await session.commit()
        await session.refresh(active_conversation)

        # Find active conversation
        found = await conversation_service.find_active_conversation(
            customer_id=customer.id
        )

        assert found is not None
        assert found.id == active_conversation.id

    @pytest.mark.asyncio
    async def test_active_conversation_not_found_when_closed(self, session: AsyncSession):
        """Test active conversation not found when all are closed."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com"
        )

        # Create closed conversation
        closed_conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.CLOSED,
            ended_at=datetime.now(timezone.utc)
        )
        session.add(closed_conversation)
        await session.commit()

        # Should not find active conversation
        found = await conversation_service.find_active_conversation(
            customer_id=customer.id
        )

        assert found is None

    @pytest.mark.asyncio
    async def test_conversation_linking_metadata(self, session: AsyncSession):
        """Test linking conversations via metadata."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com"
        )

        # Create two conversations
        conversation1 = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation1)
        await session.commit()
        await session.refresh(conversation1)

        conversation2 = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.WEB_FORM,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation2)
        await session.commit()
        await session.refresh(conversation2)

        # Link conversation2 to conversation1
        await conversation_service.link_conversation_to_existing(
            new_conversation_id=conversation2.id,
            existing_conversation_id=conversation1.id
        )

        # Verify metadata updated
        await session.refresh(conversation2)
        assert 'related_conversation_id' in conversation2.metadata_
        assert conversation2.metadata_['related_conversation_id'] == str(conversation1.id)
        assert conversation2.metadata_['continuation_detected'] is True

    @pytest.mark.asyncio
    async def test_reopen_closed_conversation(self, session: AsyncSession):
        """Test reopening a closed conversation."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com"
        )

        # Create and close conversation
        conversation = Conversation(
            customer_id=customer.id,
            initial_channel=Channel.EMAIL,
            status=ConversationStatus.ACTIVE
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        # Close it
        await conversation_service.close_conversation(conversation.id)
        await session.refresh(conversation)
        assert conversation.status == ConversationStatus.CLOSED
        assert conversation.ended_at is not None

        # Reopen it
        await conversation_service.reopen_conversation(conversation.id)
        await session.refresh(conversation)
        assert conversation.status == ConversationStatus.ACTIVE
        assert conversation.ended_at is None

    @pytest.mark.asyncio
    async def test_cross_channel_same_customer_different_identifiers(self, session: AsyncSession):
        """Test customer using different identifiers on different channels."""
        identification_service = CustomerIdentificationService(session)

        # Customer uses email on web form
        customer_by_email = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com",
            name="John Doe"
        )

        # Later, link phone when they use WhatsApp
        await identification_service.link_phone_to_customer(
            customer_id=customer_by_email.id,
            phone="+1234567890"
        )

        # When they use WhatsApp again, should find same customer
        customer_by_phone = await identification_service.find_customer_by_any_identifier(
            phone="+1234567890"
        )

        assert customer_by_phone is not None
        assert customer_by_phone.id == customer_by_email.id

        # Verify both identifiers exist
        identifiers = await identification_service.get_customer_identifiers(customer_by_email.id)
        assert len(identifiers) == 2

    @pytest.mark.asyncio
    async def test_conversation_history_ordering(self, session: AsyncSession):
        """Test conversation history is ordered by most recent first."""
        identification_service = CustomerIdentificationService(session)
        conversation_service = ConversationService(session)

        # Create customer
        customer = await identification_service.find_or_create_customer_by_email(
            email="customer@example.com"
        )

        # Create conversations with different timestamps
        import time
        conversations = []
        for i in range(3):
            conversation = Conversation(
                customer_id=customer.id,
                initial_channel=Channel.EMAIL,
                status=ConversationStatus.ACTIVE
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            conversations.append(conversation)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Get history
        history = await conversation_service.get_customer_conversation_history(
            customer_id=customer.id
        )

        # Should be ordered by most recent first
        assert len(history) == 3
        # Most recent conversation should be first
        assert history[0]['conversation_id'] == str(conversations[2].id)
        assert history[2]['conversation_id'] == str(conversations[0].id)
