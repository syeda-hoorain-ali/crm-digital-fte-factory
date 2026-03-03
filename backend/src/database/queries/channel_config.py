"""ChannelConfig CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List

from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    ChannelConfig,
    Channel,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ChannelConfig CRUD Operations (T026)
# ============================================================================

async def create_channel_config(
    session: AsyncSession,
    channel: Channel,
    config: dict,
    enabled: bool = True,
) -> ChannelConfig:
    """
    Create a new channel configuration.

    Args:
        session: Database session
        channel: Communication channel
        config: Channel-specific configuration
        enabled: Whether channel is active

    Returns:
        ChannelConfig: Created channel config instance
    """
    channel_config = ChannelConfig(
        channel=channel,
        config=config,
        enabled=enabled,
    )
    session.add(channel_config)
    await session.flush()
    await session.refresh(channel_config)
    return channel_config


async def get_channel_config(
    session: AsyncSession,
    channel: Channel,
) -> ChannelConfig | None:
    """
    Get channel configuration by channel type.

    Args:
        session: Database session
        channel: Communication channel

    Returns:
        ChannelConfig | None: Channel config or None if not found
    """
    stmt = select(ChannelConfig).where(col(ChannelConfig.channel) == channel)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_channel_config(
    session: AsyncSession,
    channel: Channel,
    config: dict | None = None,
    is_active: bool | None = None,
) -> ChannelConfig | None:
    """
    Update channel configuration.

    Args:
        session: Database session
        channel: Communication channel
        config: New configuration (optional)
        is_active: New active status (optional)

    Returns:
        ChannelConfig | None: Updated config or None if not found
    """
    channel_config = await get_channel_config(session, channel)

    if not channel_config:
        return None

    if config is not None:
        channel_config.config = config
    if is_active is not None:
        channel_config.is_active = is_active

    channel_config.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(channel_config)
    return channel_config


async def list_active_channels(
    session: AsyncSession,
) -> List[ChannelConfig]:
    """
    List all active channel configurations.

    Args:
        session: Database session

    Returns:
        List[ChannelConfig]: List of active channel configs
    """
    stmt = select(ChannelConfig).where(col(ChannelConfig.enabled) == True)
    result = await session.execute(stmt)
    return list(result.scalars().all())
