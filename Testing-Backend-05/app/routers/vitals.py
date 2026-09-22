from fastapi import APIRouter, HTTPException

from app.schemas.vitals import (
    AlertScenarioSource,
    AlertScenarioStartRequest,
    StableVitalsSource,
    StableVitalsStartRequest,
)
from app.state import (
    alert_scenario_service,
    stable_vitals_service,
)


router = APIRouter(
    prefix="/testing/vitals",
    tags=["Testing - Vitals"],
)


# ============================================================
# Stable vitals
# ============================================================

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


# ============================================================
# Alert scenarios
# ============================================================

@router.post(
    "/scenarios/start",
    response_model=AlertScenarioSource,
)
async def start_alert_scenario(
    request: AlertScenarioStartRequest,
):
    try:
        return await alert_scenario_service.start_source(
            request
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/scenarios/{source_id}/stop",
    response_model=AlertScenarioSource,
)
async def stop_alert_scenario(
    source_id: str,
):
    source = await alert_scenario_service.stop_source(
        source_id
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Alert scenario source "
                f"'{source_id}' not found."
            ),
        )

    return source


@router.get(
    "/scenarios",
    response_model=list[AlertScenarioSource],
)
def list_alert_scenarios():
    return alert_scenario_service.list_sources()


@router.get(
    "/scenarios/{source_id}",
    response_model=AlertScenarioSource,
)
def get_alert_scenario(
    source_id: str,
):
    source = alert_scenario_service.get_source(
        source_id
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Alert scenario source "
                f"'{source_id}' not found."
            ),
        )

    return source