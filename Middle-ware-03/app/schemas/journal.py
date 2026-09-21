from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JournalEventRequest(BaseModel):
    journal_id: str

    patient_id: str
    encounter_id: str

    author_id: str
    author_role: str

    content: str

    timestamp: Optional[datetime] = None
    episode_id: Optional[str] = None


class JournalFixedActivityRequest(BaseModel):
    journal_id: str

    patient_id: str
    encounter_id: str

    author_id: str
    author_role: str

    content: str

    start_time: datetime
    end_time: datetime

    start_reason: Optional[str] = None
    end_reason: Optional[str] = None

    episode_id: Optional[str] = None


class JournalOngoingActivityStartRequest(BaseModel):
    journal_id: str

    patient_id: str
    encounter_id: str

    author_id: str
    author_role: str

    content: str

    start_time: Optional[datetime] = None
    start_reason: Optional[str] = None

    episode_id: Optional[str] = None


class JournalOngoingActivityEndRequest(BaseModel):
    end_time: Optional[datetime] = None
    end_reason: Optional[str] = None

    actor_id: Optional[str] = None
    actor_role: Optional[str] = None