import asyncio
import random
from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from app.messaging.kafka import KafkaProducer
from app.schemas.vitals import (
    StableVitalsSource,
    StableVitalsStartRequest,
    VitalReading,
)


class StableVitalsService:
    def __init__(
        self,
        kafka_producer: KafkaProducer,
    ):
        self._kafka_producer = kafka_producer

        self._sources: dict[
            str,
            StableVitalsSource,
        ] = {}

        self._tasks: dict[
            str,
            asyncio.Task,
        ] = {}

    async def start_source(
        self,
        request: StableVitalsStartRequest,
    ) -> StableVitalsSource:
        source_id = (
            f"VS-{uuid4().hex[:8].upper()}"
        )

        source = StableVitalsSource(
            source_id=source_id,
            patient_id=request.patient_id,
            status="RUNNING",
            started_at=request.start_time,
            metrics=request.metrics,
            interval_seconds=request.interval_seconds,
            last_reading=None,
        )

        self._sources[source_id] = source

        task = asyncio.create_task(
            self._run_generator(source_id)
        )

        self._tasks[source_id] = task

        return source

    async def stop_source(
        self,
        source_id: str,
    ) -> StableVitalsSource | None:
        source = self._sources.get(source_id)

        if source is None:
            return None

        task = self._tasks.pop(
            source_id,
            None,
        )

        if task is not None:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        stopped_source = source.model_copy(
            update={
                "status": "STOPPED",
            }
        )

        self._sources[source_id] = stopped_source

        return stopped_source

    def list_sources(
        self,
    ) -> list[StableVitalsSource]:
        return list(
            self._sources.values()
        )

    def get_source(
        self,
        source_id: str,
    ) -> StableVitalsSource | None:
        return self._sources.get(
            source_id
        )

    async def _run_generator(
        self,
        source_id: str,
    ) -> None:
        while True:
            source = self._sources.get(
                source_id
            )

            if source is None:
                return

            if source.status != "RUNNING":
                return

            reading = self._generate_reading(
                source
            )

            self._sources[source_id] = (
                source.model_copy(
                    update={
                        "last_reading": reading,
                    }
                )
            )

            await self._publish_reading(
                reading
            )

            await asyncio.sleep(
                source.interval_seconds
            )

    async def _publish_reading(
        self,
        reading: VitalReading,
    ) -> None:
        await self._kafka_producer.publish(
            topic=settings.kafka_vitals_topic,
            key=reading.patient_id,
            payload=reading.model_dump(
                mode="json"
            ),
        )

    def _generate_reading(
        self,
        source: StableVitalsSource,
    ) -> VitalReading:
        timestamp = datetime.now(
            timezone.utc
        )

        metrics: dict[str, float] = {}

        for (
            metric_name,
            base_value,
        ) in source.metrics.items():
            metrics[metric_name] = (
                self._stable_value(
                    base_value
                )
            )

        reading = VitalReading(
            source_id=source.source_id,
            patient_id=source.patient_id,
            timestamp=timestamp,
            metrics=metrics,
        )

        print(
            "[DUMMY VITALS]",
            reading.model_dump(
                mode="json"
            ),
        )

        return reading

    @staticmethod
    def _stable_value(
        base_value: float,
    ) -> float:
        variation = random.uniform(
            -0.5,
            0.5,
        )

        return round(
            base_value + variation,
            2,
        )

    async def shutdown(self) -> None:
        tasks = list(
            self._tasks.items()
        )

        self._tasks.clear()

        for (
            source_id,
            task,
        ) in tasks:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        for (
            source_id,
            source,
        ) in list(
            self._sources.items()
        ):
            self._sources[source_id] = (
                source.model_copy(
                    update={
                        "status": "STOPPED",
                    }
                )
            )