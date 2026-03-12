"""Conversation service for cross-channel continuity detection."""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone

from sqlmodel import col, select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import (
    Conversation,
    Message,
    Ticket,
    Channel,
    ConversationStatus,
)

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation continuity across channels."""

    def __init__(self, session: AsyncSession):
        """Initialize conversation service.

        Args:
            session: Database session
        """
        self.session = session

    async def find_active_conversation(
        self,
        customer_id: UUID,
        channel: Optional[Channel] = None,
        max_age_hours: int = 24
    ) -> Optional[Conversation]:
        """Find active conversation for customer.

        Args:
            customer_id: Customer UUID
            channel: Optional channel filter
            max_age_hours: Maximum age of conversation to consider (default 24 hours)

        Returns:
            Active conversation if found, None otherwise
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        query = select(Conversation).where(
            and_(
                Conversation.customer_id == customer_id,
                Conversation.status == ConversationStatus.ACTIVE,
                Conversation.started_at >= cutoff_time
            )
        )

        if channel:
            query = query.where(Conversation.initial_channel == channel)

        result = await self.session.execute(query.order_by(col(Conversation.started_at).desc()))
        return result.scalars().first()

    async def find_related_conversations(
        self,
        customer_id: UUID,
        max_age_hours: int = 72
    ) -> list[Conversation]:
        """Find all recent conversations for a customer across all channels.

        Args:
            customer_id: Customer UUID
            max_age_hours: Maximum age of conversations to include (default 72 hours)

        Returns:
            List of conversations ordered by most recent first
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        result = await self.session.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.customer_id == customer_id,
                    Conversation.started_at >= cutoff_time
                )
            )
            .order_by(col(Conversation.started_at).desc())
        )
        return list(result.scalars().all())

    async def detect_conversation_continuity(
        self,
        customer_id: UUID,
        new_message_content: str,
        new_channel: Channel,
        similarity_threshold: float = 0.3
    ) -> Optional[Conversation]:
        """Detect if new message continues an existing conversation.

        Uses simple keyword matching to detect if the customer is continuing
        a previous conversation on a different channel.

        Args:
            customer_id: Customer UUID
            new_message_content: Content of new message
            new_channel: Channel of new message
            similarity_threshold: Minimum similarity score (0-1) to consider continuation

        Returns:
            Existing conversation if continuity detected, None otherwise
        """
        # Get recent conversations from other channels
        recent_conversations = await self.find_related_conversations(
            customer_id=customer_id,
            max_age_hours=48  # Look back 48 hours
        )

        if not recent_conversations:
            return None

        # Extract keywords from new message (simple approach)
        new_keywords = self._extract_keywords(new_message_content)

        if not new_keywords:
            return None

        # Check each conversation for similarity
        best_match = None
        best_score = 0.0

        for conversation in recent_conversations:
            # Skip conversations on the same channel
            if conversation.initial_channel == new_channel:
                continue

            # Get recent messages from this conversation
            result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(col(Message.created_at).desc())
                .limit(5)
            )
            messages = list(result.scalars().all())

            # Calculate similarity score
            score = self._calculate_similarity(new_keywords, messages)

            if score > best_score and score >= similarity_threshold:
                best_score = score
                best_match = conversation

        if best_match:
            logger.info(
                f"Detected conversation continuity",
                extra={
                    "customer_id": str(customer_id),
                    "existing_conversation_id": str(best_match.id),
                    "existing_channel": best_match.initial_channel.value,
                    "new_channel": new_channel.value,
                    "similarity_score": best_score
                }
            )

        return best_match

    def _extract_keywords(self, text: str, min_length: int = 3) -> set[str]:
        """Extract keywords from text.

        Simple implementation: lowercase words longer than min_length,
        excluding common stop words. Uses basic stemming to normalize word forms.

        Args:
            text: Text to extract keywords from
            min_length: Minimum word length to consider

        Returns:
            Set of keywords
        """
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have',
            'been', 'were', 'what', 'when', 'where', 'which', 'their',
            'about', 'would', 'there', 'could', 'should', 'your', 'help',
            'need', 'want', 'please', 'thank', 'thanks', 'cant', 'dont',
            'wont', 'isnt', 'arent', 'wasnt', 'werent', 'still', 'into'
        }

        # Extract words
        words = text.lower().split()

        # Filter and clean
        keywords = set()
        for word in words:
            # Remove punctuation
            word = ''.join(c for c in word if c.isalnum())

            # Basic stemming - remove common suffixes
            # Handle -ting suffix (resetting -> reset)
            if word.endswith('ting') and len(word) > 5:
                word = word[:-4]
            # Handle -ing suffix (logging -> log, login -> log)
            elif word.endswith('ing') and len(word) > 4:
                word = word[:-3]
                # Handle double consonant before -ing (running -> run)
                if len(word) >= 2 and word[-1] == word[-2] and word[-1] not in 'aeiou':
                    word = word[:-1]
            # Handle -in suffix for words like "login" (login -> log)
            elif word.endswith('in') and len(word) > 4:
                word = word[:-2]
            # Handle -ed suffix
            elif word.endswith('ed') and len(word) > 3:
                word = word[:-2]
            # Handle -s suffix (accounts -> account)
            elif word.endswith('s') and len(word) > 3 and not word.endswith('ss'):
                word = word[:-1]

            # Keep if long enough and not a stop word
            if len(word) >= min_length and word not in stop_words:
                keywords.add(word)

        logger.debug(f"Extracted keywords from '{text[:50]}...': {keywords}")
        return keywords

    def _calculate_similarity(
        self,
        new_keywords: set[str],
        existing_messages: list[Message]
    ) -> float:
        """Calculate similarity between new message and existing messages.

        Args:
            new_keywords: Keywords from new message
            existing_messages: List of existing messages to compare against

        Returns:
            Similarity score between 0 and 1
        """
        if not new_keywords or not existing_messages:
            return 0.0

        # Extract keywords from all existing messages
        existing_keywords = set()
        for message in existing_messages:
            existing_keywords.update(self._extract_keywords(message.content))

        if not existing_keywords:
            return 0.0

        # Calculate Jaccard similarity (intersection over union)
        intersection = len(new_keywords & existing_keywords)
        union = len(new_keywords | existing_keywords)

        if union == 0:
            return 0.0

        return intersection / union

    async def link_conversation_to_existing(
        self,
        new_conversation_id: UUID,
        existing_conversation_id: UUID
    ) -> None:
        """Link a new conversation to an existing one.

        Updates metadata to indicate the conversations are related.

        Args:
            new_conversation_id: New conversation UUID
            existing_conversation_id: Existing conversation UUID
        """
        new_conv = await self.session.get(Conversation, new_conversation_id)
        existing_conv = await self.session.get(Conversation, existing_conversation_id)

        if not new_conv or not existing_conv:
            logger.warning(
                f"Cannot link conversations - one or both not found",
                extra={
                    "new_conversation_id": str(new_conversation_id),
                    "existing_conversation_id": str(existing_conversation_id)
                }
            )
            return

        # Update metadata to link conversations
        if not new_conv.metadata_:
            new_conv.metadata_ = {}

        new_conv.metadata_['related_conversation_id'] = str(existing_conversation_id)
        new_conv.metadata_['continuation_detected'] = True

        self.session.add(new_conv)
        await self.session.commit()

        logger.info(
            f"Linked conversations",
            extra={
                "new_conversation_id": str(new_conversation_id),
                "existing_conversation_id": str(existing_conversation_id)
            }
        )

    async def get_customer_conversation_history(
        self,
        customer_id: UUID,
        limit: int = 50,
        include_closed: bool = True
    ) -> list[dict]:
        """Get unified conversation history for a customer.

        Args:
            customer_id: Customer UUID
            limit: Maximum number of messages to return
            include_closed: Whether to include closed conversations

        Returns:
            List of conversation history items with messages
        """
        # Build query
        query = select(Conversation).where(Conversation.customer_id == customer_id)

        if not include_closed:
            query = query.where(Conversation.status != ConversationStatus.CLOSED)

        query = query.order_by(col(Conversation.started_at).desc())

        # Get conversations
        result = await self.session.execute(query)
        conversations = list(result.scalars().all())

        # Build history
        history = []

        for conversation in conversations:
            # Get messages for this conversation
            messages_result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(col(Message.created_at))
            )
            messages = list(messages_result.scalars().all())

            # Get ticket if exists
            ticket_result = await self.session.execute(
                select(Ticket)
                .where(Ticket.conversation_id == conversation.id)
            )
            ticket = ticket_result.scalars().first()

            history.append({
                'conversation_id': str(conversation.id),
                'channel': conversation.initial_channel.value,
                'status': conversation.status.value,
                'started_at': conversation.started_at.isoformat(),
                'ended_at': conversation.ended_at.isoformat() if conversation.ended_at else None,
                'ticket_id': str(ticket.id) if ticket else None,
                'ticket_status': ticket.status.value if ticket else None,
                'message_count': len(messages),
                'messages': [
                    {
                        'id': str(msg.id),
                        'role': msg.role.value,
                        'content': msg.content,
                        'channel': msg.channel.value,
                        'created_at': msg.created_at.isoformat()
                    }
                    for msg in messages[:limit]  # Limit messages per conversation
                ],
                'metadata': conversation.metadata_
            })

        return history

    async def close_conversation(
        self,
        conversation_id: UUID,
        resolution_type: Optional[str] = None
    ) -> Conversation:
        """Close a conversation.

        Args:
            conversation_id: Conversation UUID
            resolution_type: Optional resolution type

        Returns:
            Updated conversation

        Raises:
            ValueError: If conversation not found
        """
        conversation = await self.session.get(Conversation, conversation_id)

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.status = ConversationStatus.CLOSED
        conversation.ended_at = datetime.now(timezone.utc)
        if resolution_type:
            conversation.resolution_type = resolution_type

        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)

        logger.info(
            f"Closed conversation",
            extra={
                "conversation_id": str(conversation_id),
                "resolution_type": resolution_type
            }
        )

        return conversation

    async def reopen_conversation(
        self,
        conversation_id: UUID
    ) -> Conversation:
        """Reopen a closed conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Updated conversation

        Raises:
            ValueError: If conversation not found
        """
        conversation = await self.session.get(Conversation, conversation_id)

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.status = ConversationStatus.ACTIVE
        conversation.ended_at = None

        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)

        logger.info(
            f"Reopened conversation",
            extra={"conversation_id": str(conversation_id)}
        )

        return conversation
