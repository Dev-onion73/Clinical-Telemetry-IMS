from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.vitals import (
    StableVitalsSource,
    StableVitalsStartRequest,
)


class StableVitalsService:
    def __init__(self):
        self._sources: dict[str, StableVitalsSource] = {}

    def start_source(
        self,
        request: StableVitalsStartRequest,
    ) -> StableVitalsSource:
        source_id = f"VS-{uuid4().hex[:8].upper()}"

        source = StableVitalsSource(
            source_id=source_id,
            patient_id=request.patient_id,
            status="RUNNING",
            started_at=request.start_time,
            metrics=request.metrics,
            interval_seconds=request.interval_seconds,
        )

        self._sources[source_id] = source

        return source

    def stop_source(
        self,
        source_id: str,
    ) -> StableVitalsSource | None:
        source = self._sources.get(source_id)

        if source is None:
            return None

        stopped_source = source.model_copy(
            update={
                "status": "STOPPED",
            }
        )

        self._sources[source_id] = stopped_source

        return stopped_source

    def list_sources(self) -> list[StableVitalsSource]:
        return list(self._sources.values())

    def get_source(
        self,
        source_id: str,
    ) -> StableVitalsSource | None:
        return self._sources.get(source_id)