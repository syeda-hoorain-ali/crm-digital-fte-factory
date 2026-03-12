"""Kafka consumer lag monitoring."""

import logging
from typing import Optional
import asyncio

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, ConsumerGroupDescription
from aiokafka.errors import KafkaError

from ..monitoring.prometheus_metrics import update_kafka_lag

logger = logging.getLogger(__name__)


class KafkaLagMonitor:
    """Monitor Kafka consumer lag for alerting and metrics."""

    def __init__(
        self,
        bootstrap_servers: str,
        consumer_group: str,
        topics: list[str]
    ):
        """Initialize Kafka lag monitor.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            consumer_group: Consumer group to monitor
            topics: List of topics to monitor
        """
        self.bootstrap_servers = bootstrap_servers
        self.consumer_group = consumer_group
        self.topics = topics
        self.admin_client: Optional[AIOKafkaAdminClient] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._monitoring = False

    async def start(self):
        """Start the lag monitor."""
        try:
            # Initialize admin client
            self.admin_client = AIOKafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers
            )
            await self.admin_client.start()

            # Initialize consumer for offset tracking
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                enable_auto_commit=False
            )
            await self.consumer.start()

            logger.info(
                f"Kafka lag monitor started",
                extra={
                    "consumer_group": self.consumer_group,
                    "topics": self.topics
                }
            )

        except Exception as e:
            logger.error(f"Failed to start Kafka lag monitor: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the lag monitor."""
        self._monitoring = False

        if self.consumer:
            await self.consumer.stop()

        if self.admin_client:
            await self.admin_client.close()

        logger.info("Kafka lag monitor stopped")

    async def get_consumer_lag(self) -> dict[str, dict[int, int]]:
        """Get current consumer lag for all topics and partitions.

        Returns:
            Dictionary mapping topic -> partition -> lag
        """
        if not self.consumer:
            raise RuntimeError("Lag monitor not started")

        lag_info = {}

        try:
            # Get assigned partitions
            partitions = self.consumer.assignment()

            for tp in partitions:
                topic = tp.topic
                partition = tp.partition

                # Get current consumer position
                position = await self.consumer.position(tp)

                # Get high water mark (latest offset)
                end_offsets = await self.consumer.end_offsets([tp])
                high_water_mark = end_offsets[tp]

                # Calculate lag
                lag = high_water_mark - position

                if topic not in lag_info:
                    lag_info[topic] = {}

                lag_info[topic][partition] = lag

                # Update Prometheus metric
                update_kafka_lag(
                    topic=topic,
                    partition=partition,
                    consumer_group=self.consumer_group,
                    lag=lag
                )

                logger.debug(
                    f"Consumer lag",
                    extra={
                        "topic": topic,
                        "partition": partition,
                        "position": position,
                        "high_water_mark": high_water_mark,
                        "lag": lag
                    }
                )

        except KafkaError as e:
            logger.error(f"Error getting consumer lag: {e}", exc_info=True)
            raise

        return lag_info

    async def monitor_continuously(self, interval_seconds: int = 60):
        """Continuously monitor consumer lag.

        Args:
            interval_seconds: Interval between lag checks
        """
        self._monitoring = True

        logger.info(
            f"Starting continuous lag monitoring",
            extra={"interval_seconds": interval_seconds}
        )

        while self._monitoring:
            try:
                lag_info = await self.get_consumer_lag()

                # Check for high lag and log warnings
                for topic, partitions in lag_info.items():
                    for partition, lag in partitions.items():
                        if lag > 1000:
                            logger.warning(
                                f"High consumer lag detected",
                                extra={
                                    "topic": topic,
                                    "partition": partition,
                                    "lag": lag,
                                    "consumer_group": self.consumer_group
                                }
                            )

            except Exception as e:
                logger.error(
                    f"Error in lag monitoring loop: {e}",
                    exc_info=True
                )

            # Wait before next check
            await asyncio.sleep(interval_seconds)

    async def get_lag_summary(self) -> dict:
        """Get summary of consumer lag across all topics.

        Returns:
            Summary with total lag, max lag, and per-topic stats
        """
        lag_info = await self.get_consumer_lag()

        total_lag = 0
        max_lag = 0
        topic_stats = {}

        for topic, partitions in lag_info.items():
            topic_lag = sum(partitions.values())
            topic_max_lag = max(partitions.values()) if partitions else 0

            total_lag += topic_lag
            max_lag = max(max_lag, topic_max_lag)

            topic_stats[topic] = {
                "total_lag": topic_lag,
                "max_lag": topic_max_lag,
                "partitions": len(partitions),
                "avg_lag": topic_lag / len(partitions) if partitions else 0
            }

        return {
            "consumer_group": self.consumer_group,
            "total_lag": total_lag,
            "max_lag": max_lag,
            "topics": topic_stats
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
