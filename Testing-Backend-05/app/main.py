from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers.alerts import router as alerts_router
from app.routers.vitals import router as vitals_router
from app.state import (
    alert_injector_service,
    alert_scenario_service,
    kafka_producer,
    stable_vitals_service,
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    print(
        "Testing Backend starting..."
    )

    await kafka_producer.start()

    print(
        "Kafka producer started."
    )

    yield

    print(
        "Testing Backend shutting down..."
    )

    await alert_injector_service.shutdown()

    await alert_scenario_service.shutdown()

    await stable_vitals_service.shutdown()

    await kafka_producer.stop()

    print(
        "Kafka producer stopped."
    )


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Testing and synthetic-data backend "
        "for Healthcare Incident Management."
    ),
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


app.include_router(
    vitals_router
)

app.include_router(
    alerts_router
)