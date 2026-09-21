import json

from aiokafka import AIOKafkaProducer

from app.config import settings


class KafkaProducer:
    def __init__(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
        )

    async def start(self) -> None:
        await self._producer.start()

    async def stop(self) -> None:
        await self._producer.stop()

    async def publish(
        self,
        *,
        topic: str,
        key: str,
        payload: dict,
    ) -> None:
        value = json.dumps(
            payload,
            default=str,
        ).encode("utf-8")

        await self._producer.send_and_wait(
            topic,
            key=key.encode("utf-8"),
            value=value,
        )