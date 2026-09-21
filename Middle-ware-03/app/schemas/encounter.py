from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EncounterType(str, Enum):
    EMERGENCY = "EMERGENCY"
    ROUTINE = "ROUTINE"
    FOLLOW_UP = "FOLLOW_UP"
    PROCEDURE = "PROCEDURE"
    OTHER = "OTHER"


class CareSetting(str, Enum):
    INPATIENT = "INPATIENT"
    OUTPATIENT = "OUTPATIENT"
    EMERGENCY = "EMERGENCY"


class EncounterStartRequest(BaseModel):
    encounter_id: str
    patient_id: str

    encounter_type: EncounterType
    care_setting: CareSetting

    start_reason: str
    started_by: str
    started_by_role: str = "ADMIN"

    start_details: Optional[str] = None
    start_time: Optional[datetime] = None


class EncounterCloseRequest(BaseModel):
    end_reason: str
    ended_by: str
    actor_role: str = "ADMIN"

    end_details: Optional[str] = None
    end_time: Optional[datetime] = None