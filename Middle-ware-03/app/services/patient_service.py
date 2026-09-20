from datetime import date

from app.persistence.patients import PatientRepository


class PatientService:

    def __init__(
        self,
        repository=None,
    ):
        self.repository = repository or PatientRepository()

    def register(
        self,
        patient_id: str,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        sex: str,
        blood_group: str,
    ) -> dict:

        patient_id = patient_id.strip()
        first_name = first_name.strip()
        last_name = last_name.strip()

        if not patient_id:
            raise ValueError("Patient ID is required")

        if not first_name:
            raise ValueError("First name is required")

        if not last_name:
            raise ValueError("Last name is required")

        if date_of_birth is None:
            raise ValueError("Date of birth is required")

        if date_of_birth > date.today():
            raise ValueError(
                "Date of birth cannot be in the future"
            )

        if self.repository.get(patient_id) is not None:
            raise ValueError(
                f"Patient already exists: {patient_id}"
            )

        return self.repository.create(
            patient_id=patient_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            sex=sex,
            blood_group=blood_group,
        )

    def get(
        self,
        patient_id: str,
    ) -> dict | None:

        return self.repository.get(patient_id)

    def list_all(self) -> list[dict]:

        return self.repository.list_all()