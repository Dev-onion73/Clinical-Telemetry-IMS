from fastapi import FastAPI, HTTPException

from app.tracing.provider import configure_tracing

from app.routers import (
    encounters,
    episodes,
    journals,
)

from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
)

from app.services.patient_service import PatientService


configure_tracing()


app = FastAPI(
    title="Clinical Middleware",
    version="0.1.0",
)


patient_service = PatientService()


# =========================================================
# Routers
# =========================================================

app.include_router(
    encounters.router
)

app.include_router(
    episodes.router
)

app.include_router(
    journals.router
)


# =========================================================
# System
# =========================================================

@app.get("/")
def root():
    return {
        "service": "clinical-middleware",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# =========================================================
# Patients
# =========================================================

@app.post("/patients")
def register_patient(
    patient: PatientCreate,
):
    try:
        return patient_service.register(
            patient_id=patient.patient_id,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            sex=patient.sex.value,
            blood_group=patient.blood_group.value,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get(
    "/patients",
    response_model=list[PatientResponse],
)
def list_patients():

    return patient_service.list_all()


@app.get(
    "/patients/{patient_id}",
    response_model=PatientResponse,
)
def get_patient(
    patient_id: str,
):

    patient = patient_service.get(
        patient_id
    )

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient not found: {patient_id}",
        )

    return patient