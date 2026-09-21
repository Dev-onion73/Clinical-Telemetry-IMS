from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EpisodeStartFromJournalRequest(BaseModel):
    episode_id: str
    journal_id: str

    patient_id: str
    encounter_id: str

    initiated_by: str
    initiation_reason: str

    author_role: str
    content: str

    start_time: Optional[datetime] = None


class EpisodeCloseRequest(BaseModel):
    closure_by: str
    end_time: Optional[datetime] = None