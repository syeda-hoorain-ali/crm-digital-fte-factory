"""Kafka topic definitions and naming conventions."""

from enum import Enum


class KafkaTopic(str, Enum):
    """Kafka topic names following customer-intake.{channel}.{type} convention."""

    # Channel-specific inbound topics
    EMAIL_INBOUND = "customer-intake.email.inbound"
    WHATSAPP_INBOUND = "customer-intake.whatsapp.inbound"
    WEBFORM_INBOUND = "customer-intake.webform.inbound"

    # Unified inbound topic for agent consumption
    ALL_INBOUND = "customer-intake.all.inbound"

    # Outbound topics (if needed for responses)
    EMAIL_OUTBOUND = "customer-intake.email.outbound"
    WHATSAPP_OUTBOUND = "customer-intake.whatsapp.outbound"
    WEBFORM_OUTBOUND = "customer-intake.webform.outbound"


def get_inbound_topic(channel: str) -> str:
    """Get inbound topic name for a channel.

    Args:
        channel: Channel name (email, whatsapp, webform)

    Returns:
        Kafka topic name (string value)
    """
    topic_map = {
        "email": KafkaTopic.EMAIL_INBOUND.value,
        "whatsapp": KafkaTopic.WHATSAPP_INBOUND.value,
        "webform": KafkaTopic.WEBFORM_INBOUND.value,
        "web_form": KafkaTopic.WEBFORM_INBOUND.value,
    }
    return topic_map.get(channel.lower(), KafkaTopic.ALL_INBOUND.value)


def get_outbound_topic(channel: str) -> str:
    """Get outbound topic name for a channel.

    Args:
        channel: Channel name (email, whatsapp, webform)

    Returns:
        Kafka topic name (string value)
    """
    topic_map = {
        "email": KafkaTopic.EMAIL_OUTBOUND.value,
        "whatsapp": KafkaTopic.WHATSAPP_OUTBOUND.value,
        "webform": KafkaTopic.WEBFORM_OUTBOUND.value,
        "web_form": KafkaTopic.WEBFORM_OUTBOUND.value,
    }
    return topic_map.get(channel.lower(), KafkaTopic.ALL_INBOUND.value)
