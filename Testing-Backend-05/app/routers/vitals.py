from fastapi import APIRouter, HTTPException

from app.schemas.vitals import (
    StableVitalsSource,
    StableVitalsStartRequest,
)
from app.state import stable_vitals_service


router = APIRouter(
    prefix="/testing/vitals",
    tags=["Testing - Vitals"],
)


@router.post(
    "/stable/start",
    response_model=StableVitalsSource,
)
async def start_stable_vitals(
    request: StableVitalsStartRequest,
):
    return await stable_vitals_service.start_source(
        request
    )


@router.post(
    "/stable/{source_id}/stop",
    response_model=StableVitalsSource,
)
async def stop_stable_vitals(
    source_id: str,
):
    source = await stable_vitals_service.stop_source(
        source_id
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Stable vitals source "
                f"'{source_id}' not found."
            ),
        )

    return source


@router.get(
    "/stable",
    response_model=list[StableVitalsSource],
)
def list_stable_vitals():
    return stable_vitals_service.list_sources()


@router.get(
    "/stable/{source_id}",
    response_model=StableVitalsSource,
)
def get_stable_vitals(
    source_id: str,
):
    source = stable_vitals_service.get_source(
        source_id
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Stable vitals source "
                f"'{source_id}' not found."
            ),
        )

    return source