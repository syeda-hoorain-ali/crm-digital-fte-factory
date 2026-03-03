"""Custom PostgreSQL session implementation for OpenAI Agents SDK."""

import logging
from typing import List, Literal
from uuid import UUID

from agents import TResponseInputItem
from agents.memory.session import SessionABC
from sqlalchemy.ext.asyncio import AsyncSession
from openai.types.responses import EasyInputMessageParam

from src.database.queries import (
    create_message,
    get_conversation_history,
    get_latest_message,
    delete_message,
)
from src.database.models import MessageRole, MessageDirection, Channel

logger = logging.getLogger(__name__)


class PostgresSession(SessionABC):
    """
    Custom PostgreSQL session implementation following SessionABC protocol.

    This session stores conversation history in the database instead of in-memory,
    enabling persistent conversations across agent runs and multi-channel support.
    """

    def __init__(self, session: AsyncSession, conversation_id: UUID, channel: Channel):
        """
        Initialize PostgreSQL session.

        Args:
            session: SQLAlchemy async session
            conversation_id: UUID of the conversation to manage
            channel: Communication channel for messages
        """
        self.session = session
        self.conversation_id = conversation_id
        self.channel = channel
        self._pending_tool_calls: dict[str, dict] = {}  # ← persist across calls

        logger.debug(f"Initialized PostgresSession for conversation {conversation_id}")


    async def get_items(self, limit: int | None = None) -> List[TResponseInputItem]:
        """
        Query Messages by conversation_id and transform to EasyInputMessageParam (T029).

        Returns:
            List[EasyInputMessageParam]: List of messages in SDK format
        """
        # Retrieve conversation history from database
        messages = await get_conversation_history(
            self.session,
            self.conversation_id,
            limit=limit or 1000,  # Reasonable limit for context window
        )

        # Transform database messages to SDK format
        sdk_messages: List[TResponseInputItem] = []

        for msg in messages:
            # Map database role to SDK role
            role = self._map_role_to_sdk(msg.role)

            sdk_message: EasyInputMessageParam = {
                "role": role,
                "content": msg.content
            }
            sdk_messages.append(sdk_message)

            # Reconstruct tool call pairs in correct SDK format
            if msg.tool_calls and len(msg.tool_calls) > 0:
                for tc in msg.tool_calls:
                    sdk_messages.append({
                        "type": "function_call_output",
                        "call_id": tc["call_id"],
                        "output": tc["output"],
                    })

        logger.debug(f"Retrieved {len(sdk_messages)} messages for conversation {self.conversation_id}")
        return sdk_messages


    async def add_items(self, items: List[TResponseInputItem]) -> None:
        """
        Insert Messages from EasyInputMessageParam items (T030).

        Args:
            items: List of messages in SDK format to add to the conversation
        """
        logger.debug(f"PostgresSession.add_items: Processing {len(items)} items")

        for item in items:
            # Tool call (function call from assistant)
            if isinstance(item, dict) and item.get("type") == "function_call":
                call_id = item.get("call_id", "")
                self._pending_tool_calls[call_id] = {
                    "call_id": call_id,
                    "name": item.get("name"),
                    "arguments": item.get("arguments"),
                }
                logger.debug(f"Captured tool call: {item.get("name")} (call_id: {call_id})")
                continue

            # Tool call output
            if isinstance(item, dict) and item.get("type") == "function_call_output":
                call_id = item.get("call_id", "")
                self._pending_tool_calls[call_id] = {
                    **self._pending_tool_calls.get(call_id, {}),
                    "call_id": call_id,
                    "output": item.get("output"),
                    "id": item.get("id"),
                    "status": item.get("status"),
                }
                logger.debug(f"Captured tool call output: (call_id: {call_id})")
                continue

            # Assistant message (ResponseOutputMessage object)
            if isinstance(item, dict) and item.get("role") in ("user", "assistant", "system", "developer"):
                role = self._map_role_from_sdk(item.get("role", ''))
                content = self._extract_text_from_content(item.get("content", ''))
                direction = (
                    MessageDirection.INBOUND
                    if role == MessageRole.CUSTOMER
                    else MessageDirection.OUTBOUND
                )

                tool_calls_to_store = []
                if self._pending_tool_calls:
                    tool_calls_to_store = list(self._pending_tool_calls.copy().values())
                    self._pending_tool_calls.clear()
                

                await create_message(
                    self.session,
                    conversation_id=self.conversation_id,
                    role=role,
                    content=content,
                    direction=direction,
                    channel=self.channel,
                    tool_calls=tool_calls_to_store,
                )

                logger.debug(f"Attaching {len(tool_calls_to_store)} tool calls to {role} message")
                continue

            logger.warning(f"Unhandled item type in add_items: {type(item)} - {item}")

    async def pop_item(self) -> EasyInputMessageParam | None:
        """
        Delete most recent Message by conversation_id (T031).

        Returns:
            EasyInputMessageParam | None: The deleted message or None if conversation is empty
        """
        # Get the latest message
        latest_message = await get_latest_message(self.session, self.conversation_id)

        if not latest_message:
            logger.debug(
                f"No messages to pop for conversation {self.conversation_id}"
            )
            return None

        # Transform to SDK format before deletion
        role = self._map_role_to_sdk(latest_message.role)
        sdk_message: EasyInputMessageParam = {
            "role": role,
            "content": latest_message.content,
        }

        # Delete the message
        deleted = await delete_message(self.session, latest_message.id)

        if deleted:
            logger.debug(
                f"Popped message {latest_message.id} from conversation {self.conversation_id}"
            )
            return sdk_message
        else:
            logger.warning(
                f"Failed to delete message {latest_message.id} from conversation {self.conversation_id}"
            )
            return None


    async def clear_session(self) -> None:
        """
        No-op implementation to preserve message data (T032).

        We intentionally do NOT delete messages to maintain conversation history
        for analytics, debugging, and customer service quality assurance.
        """
        logger.debug(
            f"clear_session called for conversation {self.conversation_id} - "
            "preserving message data (no-op)"
        )
        pass


    @staticmethod
    def _map_role_to_sdk(role: MessageRole) -> Literal["user", "assistant", "system", "developer"]:
        """
        Map database MessageRole to SDK role string.

        Args:
            role: Database message role

        Returns:
            str: SDK role string
        """
        role_mapping = {
            MessageRole.CUSTOMER: "user",
            MessageRole.AGENT: "assistant",
            MessageRole.SYSTEM: "system",
        }
        return role_mapping.get(role, "user")


    @staticmethod
    def _map_role_from_sdk(sdk_role: str) -> MessageRole:
        """
        Map SDK role string to database MessageRole.

        Args:
            sdk_role: SDK role string

        Returns:
            MessageRole: Database message role
        """
        role_mapping = {
            "user": MessageRole.CUSTOMER,
            "assistant": MessageRole.AGENT,
            "system": MessageRole.SYSTEM,
        }
        return role_mapping.get(sdk_role, MessageRole.CUSTOMER)

    @staticmethod
    def _extract_text_from_content(content) -> str:
        """
        Extract actual text from SDK content format.

        The SDK returns content in various formats:
        - String: "Hello" -> return as-is
        - List of dicts: [{'text': 'Hello', 'type': 'output_text', ...}] -> extract 'text' field
        - List of strings: ['Hello', 'World'] -> join with space

        Args:
            content: Content in SDK format (str, list, or dict)

        Returns:
            str: Extracted text content
        """
        # If content is already a string, return it
        if isinstance(content, str):
            return content

        # If content is a list, extract text from each item
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict):
                    # Extract 'text' field from dict
                    if 'text' in item:
                        texts.append(item['text'])
                    elif 'content' in item:
                        texts.append(str(item['content']))
                elif isinstance(item, str):
                    texts.append(item)
            return ' '.join(texts) if texts else ''

        # If content is a dict, try to extract text field
        if isinstance(content, dict):
            if 'text' in content:
                return content['text']
            elif 'content' in content:
                return str(content['content'])

        # Fallback: convert to string
        return str(content)
