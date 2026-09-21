from fastapi import APIRouter, HTTPException

from app.schemas.episode import (
    EpisodeCloseRequest,
    EpisodeStartFromJournalRequest,
)
from app.services.episode_service import EpisodeService


router = APIRouter(
    prefix="/episodes",
    tags=["episodes"],
)


episode_service = EpisodeService()


@router.post("/from-journal")
def start_episode_from_journal(
    request: EpisodeStartFromJournalRequest,
):
    try:
        return episode_service.start_from_journal(
            episode_id=request.episode_id,
            journal_id=request.journal_id,
            patient_id=request.patient_id,
            encounter_id=request.encounter_id,
            initiated_by=request.initiated_by,
            initiation_reason=request.initiation_reason,
            author_role=request.author_role,
            content=request.content,
            start_time=request.start_time,
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


@router.get("/{episode_id}")
def get_episode(
    episode_id: str,
):
    episode = episode_service.get(
        episode_id
    )

    if episode is None:
        raise HTTPException(
            status_code=404,
            detail=f"Episode not found: {episode_id}",
        )

    return episode


@router.post("/{episode_id}/close")
def close_episode(
    episode_id: str,
    request: EpisodeCloseRequest,
):
    try:
        return episode_service.close(
            episode_id=episode_id,
            closure_by=request.closure_by,
            end_time=request.end_time,
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