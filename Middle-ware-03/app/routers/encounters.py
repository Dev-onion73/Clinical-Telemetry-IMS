from fastapi import APIRouter, HTTPException

from app.schemas.encounter import (
    EncounterCloseRequest,
    EncounterStartRequest,
)
from app.services.encounter_service import EncounterService


router = APIRouter(
    prefix="/encounters",
    tags=["encounters"],
)


encounter_service = EncounterService()


@router.post("")
def start_encounter(
    request: EncounterStartRequest,
):
    try:
        return encounter_service.start(
            encounter_id=request.encounter_id,
            patient_id=request.patient_id,
            encounter_type=request.encounter_type.value,
            care_setting=request.care_setting.value,
            start_reason=request.start_reason,
            started_by=request.started_by,
            start_details=request.start_details,
            start_time=request.start_time,
            started_by_role=request.started_by_role,
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


@router.get("/{encounter_id}")
def get_encounter(
    encounter_id: str,
):
    encounter = encounter_service.get(
        encounter_id
    )

    if encounter is None:
        raise HTTPException(
            status_code=404,
            detail=f"Encounter not found: {encounter_id}",
        )

    return encounter


@router.post("/{encounter_id}/close")
def close_encounter(
    encounter_id: str,
    request: EncounterCloseRequest,
):
    try:
        encounter_service.close(
            encounter_id=encounter_id,
            end_reason=request.end_reason,
            ended_by=request.ended_by,
            end_details=request.end_details,
            end_time=request.end_time,
            actor_role=request.actor_role,
        )

        encounter = encounter_service.get(
            encounter_id
        )

        if encounter is None:
            raise RuntimeError(
                "Encounter disappeared after closure"
            )

        return encounter

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