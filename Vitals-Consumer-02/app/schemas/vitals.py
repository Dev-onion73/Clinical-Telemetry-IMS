from datetime import datetime

from pydantic import BaseModel, Field


class VitalReading(BaseModel):
    source_id: str = Field(min_length=1)

    patient_id: str = Field(min_length=1)
    encounter_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)

    timestamp: datetime

    metrics: dict[str, float]