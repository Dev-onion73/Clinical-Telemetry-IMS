from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers.vitals import router as vitals_router
from app.state import (
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