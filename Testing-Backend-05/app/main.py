from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers.vitals import router as vitals_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Testing Backend starting...")

    yield

    print("Testing Backend shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Testing and synthetic-data backend for Healthcare Incident Management.",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


app.include_router(vitals_router)