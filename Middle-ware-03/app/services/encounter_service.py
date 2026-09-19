from datetime import datetime, timezone
from typing import Any, Optional

from app.persistence.encounters import EncounterRepository
from app.services.trace_service import TraceService
from app.tracing.context import serialize_span_context


class EncounterService:

    def __init__(
        self,
        repository: Optional[EncounterRepository] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.repository = repository or EncounterRepository()
        self.trace_service = trace_service or TraceService()

    def start(
        self,
        encounter_id: str,
        patient_id: str,
        encounter_type: str,
        care_setting: str,
        start_reason: str,
        started_by: str,
        start_details: Optional[str] = None,
        start_time: Optional[datetime] = None,
        started_by_role: str = "ADMIN",
    ) -> dict[str, Any]:

        if not start_reason.strip():
            raise ValueError(
                "start_reason is required"
            )

        if not started_by.strip():
            raise ValueError(
                "started_by is required"
            )

        if start_time is None:
            start_time = datetime.now(timezone.utc)

        # Prevent duplicate encounter creation.
        existing = self.repository.get(
            encounter_id
        )

        if existing is not None:
            raise RuntimeError(
                f"Encounter already exists: {encounter_id}"
            )

        # ----------------------------------------------------
        # 1. Persist Encounter
        # ----------------------------------------------------

        encounter = self.repository.create(
            encounter_id=encounter_id,
            patient_id=patient_id,
            encounter_type=encounter_type,
            care_setting=care_setting,
            start_time=start_time,
            start_reason=start_reason,
            started_by=started_by,
            start_details=start_details,
        )

        # ----------------------------------------------------
        # 2. Create root Encounter span
        # ----------------------------------------------------

        try:

            encounter_span = (
                self.trace_service.start_encounter(
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    encounter_type=encounter_type,
                    start_reason=start_reason,
                    actor_id=started_by,
                    actor_role="ADMIN",
                    start_time=start_time,
                )
            )

            # ------------------------------------------------
            # 3. Extract tracing identity
            # ------------------------------------------------

            trace_identity = serialize_span_context(
                encounter_span
            )

            trace_id = trace_identity["trace_id"]
            span_id = trace_identity["span_id"]

            # ------------------------------------------------
            # 4. Persist tracing identity
            # ------------------------------------------------

            self.repository.update_trace_identity(
                encounter_id=encounter_id,
                trace_id=trace_id,
                span_id=span_id,
            )

            # Add persisted identifiers to returned object.
            encounter["trace_id"] = trace_id
            encounter["span_id"] = span_id

            return encounter

        except Exception:

            # The database row exists but tracing failed.
            #
            # For this prototype, clean up the database row
            # rather than leaving an encounter that cannot be
            # associated with its root trace.

            self._delete_created_encounter(
                encounter_id
            )

            raise

    def close(
        self,
        encounter_id: str,
        end_reason: str,
        ended_by: str,
        end_details: Optional[str] = None,
        end_time: Optional[datetime] = None,
        actor_role: str = "ADMIN",
    ) -> None:

        if not end_reason.strip():
            raise ValueError(
                "end_reason is required"
            )

        if not ended_by.strip():
            raise ValueError(
                "ended_by is required"
            )

        if end_time is None:
            end_time = datetime.now(timezone.utc)

        encounter = self.repository.get(
            encounter_id
        )

        if encounter is None:
            raise RuntimeError(
                f"Encounter not found: {encounter_id}"
            )

        if encounter["status"] == "CLOSED":
            raise RuntimeError(
                f"Encounter is already closed: "
                f"{encounter_id}"
            )

        # ----------------------------------------------------
        # 1. Persist closure
        # ----------------------------------------------------

        self.repository.close(
            encounter_id=encounter_id,
            end_time=end_time,
            end_reason=end_reason,
            ended_by=ended_by,
            end_details=end_details,
        )

        # ----------------------------------------------------
        # 2. End live Encounter span
        # ----------------------------------------------------

        self.trace_service.end_encounter(
            encounter_id=encounter_id,
            end_time=end_time,
            end_reason=end_reason,
            actor_id=ended_by,
            actor_role=actor_role,
        )

    def get(
        self,
        encounter_id: str,
    ) -> Optional[dict[str, Any]]:

        return self.repository.get(
            encounter_id
        )

    def _delete_created_encounter(
        self,
        encounter_id: str,
    ) -> None:

        self.repository.delete(
            encounter_id
        )