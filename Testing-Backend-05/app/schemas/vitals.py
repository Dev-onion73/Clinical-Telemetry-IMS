from datetime import datetime

from pydantic import BaseModel, Field


class StableVitalsStartRequest(BaseModel):
    patient_id: str = Field(min_length=1)

    start_time: datetime

    metrics: dict[str, float] = Field(
        min_length=1,
    )

    interval_seconds: float = Field(
        default=1.0,
        gt=0,
    )


class StableVitalsSource(BaseModel):
    source_id: str
    patient_id: str

    status: str

    started_at: datetime

    metrics: dict[str, float]

    interval_seconds: float