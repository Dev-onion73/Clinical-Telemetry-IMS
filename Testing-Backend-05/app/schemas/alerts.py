from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.vitals import VitalReading


class ScenarioType(str, Enum):
    SEED = "seed"
    THRESHOLD = "threshold"
    TREND = "trend"


# ============================================================================
# One-shot alert injection
# ============================================================================

class AlertInjectionRequest(BaseModel):
    scenario: str = Field(
        min_length=1,
    )

    patient_id: str = Field(
        min_length=1,
    )

    encounter_id: str = Field(
        min_length=1,
    )

    device_id: str = Field(
        min_length=1,
    )

    # Timestamp written onto the generated VitalReading.
    #
    # The API call itself is executed immediately.
    spoof_timestamp: datetime | None = None


class AlertInjectionResponse(BaseModel):
    injection_id: str

    source_id: str

    scenario: str

    scenario_type: str

    status: str

    spoof_timestamp: datetime

    injected_at: datetime

    message: str


# ============================================================================
# Continuous threshold alert
# ============================================================================

class AlertScenarioStartRequest(BaseModel):
    patient_id: str = Field(
        min_length=1,
    )

    encounter_id: str = Field(
        min_length=1,
    )

    device_id: str = Field(
        min_length=1,
    )

    # Real process start time.
    #
    # This is NOT a scheduled execution time.
    start_time: datetime

    scenario: str = Field(
        min_length=1,
    )

    interval_seconds: float = Field(
        default=1.0,
        gt=0,
    )

    # Timestamp assigned to the generated clinical data.
    #
    # If omitted, backend can use start_time.
    spoof_timestamp: datetime | None = None


# ============================================================================
# Continuous threshold source
# ============================================================================

class AlertScenarioSource(BaseModel):
    source_id: str

    patient_id: str

    encounter_id: str

    device_id: str

    status: str

    started_at: datetime

    scenario: str

    scenario_type: ScenarioType

    interval_seconds: float

    # Timestamp of the first synthetic reading.
    spoof_timestamp: datetime

    # Number of readings already emitted.
    sample_index: int = 0

    last_reading: VitalReading | None = None