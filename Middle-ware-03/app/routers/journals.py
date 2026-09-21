from fastapi import APIRouter, HTTPException

from app.schemas.journal import (
    JournalEventRequest,
    JournalFixedActivityRequest,
    JournalOngoingActivityEndRequest,
    JournalOngoingActivityStartRequest,
)
from app.services.journal_service import JournalService


router = APIRouter(
    prefix="/journals",
    tags=["journals"],
)


journal_service = JournalService()


@router.post("/event")
def create_journal_event(
    request: JournalEventRequest,
):
    try:
        return journal_service.create_event(
            journal_id=request.journal_id,
            patient_id=request.patient_id,
            encounter_id=request.encounter_id,
            author_id=request.author_id,
            author_role=request.author_role,
            content=request.content,
            timestamp=request.timestamp,
            episode_id=request.episode_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )


@router.post("/activity/fixed")
def create_fixed_journal_activity(
    request: JournalFixedActivityRequest,
):
    try:
        return journal_service.create_fixed_activity(
            journal_id=request.journal_id,
            patient_id=request.patient_id,
            encounter_id=request.encounter_id,
            author_id=request.author_id,
            author_role=request.author_role,
            content=request.content,
            start_time=request.start_time,
            end_time=request.end_time,
            start_reason=request.start_reason,
            end_reason=request.end_reason,
            episode_id=request.episode_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )


@router.post("/activity/ongoing")
def start_ongoing_journal_activity(
    request: JournalOngoingActivityStartRequest,
):
    try:
        return journal_service.start_ongoing_activity(
            journal_id=request.journal_id,
            patient_id=request.patient_id,
            encounter_id=request.encounter_id,
            author_id=request.author_id,
            author_role=request.author_role,
            content=request.content,
            start_time=request.start_time,
            start_reason=request.start_reason,
            episode_id=request.episode_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )


@router.post(
    "/activity/ongoing/{journal_id}/end"
)
def end_ongoing_journal_activity(
    journal_id: str,
    request: JournalOngoingActivityEndRequest,
):
    try:
        journal_service.end_ongoing_activity(
            journal_id=journal_id,
            end_time=request.end_time,
            end_reason=request.end_reason,
            actor_id=request.actor_id,
            actor_role=request.actor_role,
        )

        return {
            "journal_id": journal_id,
            "status": "CLOSED",
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )