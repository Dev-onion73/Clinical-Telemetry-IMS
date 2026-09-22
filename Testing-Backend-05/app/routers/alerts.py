from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.alerts import (
    AlertInjectionRequest,
    AlertInjectionResponse,
    AlertScenarioStartRequest,
)
from app.services.alert_scenarios import (
    AlertScenarioService,
)
from app.state import (
    alert_injector_service,
    alert_scenario_service,
)


router = APIRouter(
    prefix="/testing/alerts",
    tags=["testing-alerts"],
)


# ============================================================================
# Catalog
# ============================================================================

@router.get("/catalog")
def get_alert_catalog():
    return AlertScenarioService.catalog()


# ============================================================================
# Instantaneous one-shot alert
# ============================================================================

@router.post(
    "/inject",
    response_model=AlertInjectionResponse,
)
async def inject_alert(
    request: AlertInjectionRequest,
):
    try:
        return await alert_injector_service.inject(
            scenario=request.scenario,
            patient_id=request.patient_id,
            encounter_id=request.encounter_id,
            device_id=request.device_id,
            spoof_timestamp=request.spoof_timestamp,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ============================================================================
# Continuous threshold — START
# ============================================================================

@router.post(
    "/threshold/start",
)
async def start_threshold(
    request: AlertScenarioStartRequest,
):
    try:
        source = (
            await alert_scenario_service.start_threshold(
                patient_id=request.patient_id,
                encounter_id=request.encounter_id,
                device_id=request.device_id,
                scenario=request.scenario,
                start_time=request.start_time,
                interval_seconds=request.interval_seconds,
                spoof_timestamp=request.spoof_timestamp,
            )
        )

        return source.model_dump(
            mode="json"
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ============================================================================
# Continuous threshold — STOP
# ============================================================================

@router.post(
    "/threshold/{source_id}/stop",
)
async def stop_threshold(
    source_id: str,
):
    source = (
        await alert_scenario_service.stop_source(
            source_id
        )
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Threshold source "
                f"'{source_id}' not found."
            ),
        )

    return source.model_dump(
        mode="json"
    )


# ============================================================================
# Threshold sources
# ============================================================================

@router.get(
    "/threshold",
)
def get_threshold_sources():
    sources = (
        alert_scenario_service.list_sources()
    )

    return [
        source.model_dump(
            mode="json"
        )
        for source in sources
        if source.scenario_type.value
        == "threshold"
    ]


@router.get(
    "/threshold/{source_id}",
)
def get_threshold_source(
    source_id: str,
):
    source = (
        alert_scenario_service.get_source(
            source_id
        )
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Threshold source "
                f"'{source_id}' not found."
            ),
        )

    if source.scenario_type.value != "threshold":
        raise HTTPException(
            status_code=404,
            detail=(
                f"Source '{source_id}' "
                "is not a threshold source."
            ),
        )

    return source.model_dump(
        mode="json"
    )