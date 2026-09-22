import json

from aiokafka import AIOKafkaConsumer

from app.config import settings


class KafkaConsumer:
    def __init__(self):
        self._consumer = AIOKafkaConsumer(
            settings.kafka_vitals_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )

    async def start(self) -> None:
        await self._consumer.start()

    async def stop(self) -> None:
        await self._consumer.stop()

    async def messages(self):
        async for message in self._consumer:
            payload = json.loads(
                message.value.decode("utf-8")
            )

            yield payload