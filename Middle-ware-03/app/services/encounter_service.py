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
        self.repository = (
            repository
            or EncounterRepository()
        )

        self.trace_service = (
            trace_service
            or TraceService()
        )

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
            start_time = datetime.now(
                timezone.utc
            )

        # ----------------------------------------------------
        # Prevent duplicate encounter creation.
        # ----------------------------------------------------

        existing = self.repository.get(
            encounter_id
        )

        if existing is not None:
            raise RuntimeError(
                f"Encounter already exists: "
                f"{encounter_id}"
            )

        # ----------------------------------------------------
        # 1. Persist Encounter.
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

        try:

            # ------------------------------------------------
            # 2. Create the 10-second Encounter Starter Span.
            #
            # This creates the trace identity.
            # ------------------------------------------------

            encounter_span = (
                self.trace_service.start_encounter(
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    encounter_type=encounter_type,
                    start_reason=start_reason,
                    actor_id=started_by,
                    actor_role=started_by_role,
                    start_details=start_details,
                    start_time=start_time,
                )
            )

            # ------------------------------------------------
            # 3. Extract trace identity from Starter Span.
            # ------------------------------------------------

            trace_identity = (
                serialize_span_context(
                    encounter_span
                )
            )

            trace_id = (
                trace_identity["trace_id"]
            )

            span_id = (
                trace_identity["span_id"]
            )

            # ------------------------------------------------
            # 4. Persist Starter Span identity.
            # ------------------------------------------------

            self.repository.update_trace_identity(
                encounter_id=encounter_id,
                trace_id=trace_id,
                span_id=span_id,
            )

            # ------------------------------------------------
            # 5. FINISH THE STARTER.
            #
            # This is deliberately done immediately.
            #
            # The starter becomes a 10-second completed span:
            #
            #     start_time
            #         |
            #         +---- 10 sec ----+
            #
            # It is then flushed to the exporter.
            #
            # The Span remains in encounter_span_registry so
            # it can still provide the Encounter's trace
            # context to Episodes and Journals.
            # ------------------------------------------------

            self.trace_service.finish_encounter_starter(
                encounter_id=encounter_id,
                start_time=start_time,
            )

            # ------------------------------------------------
            # 6. Return persisted tracing identity.
            # ------------------------------------------------

            encounter["trace_id"] = trace_id
            encounter["span_id"] = span_id

            return encounter

        except Exception:

            # ------------------------------------------------
            # Database row exists but tracing failed.
            #
            # Clean it up for this prototype.
            # ------------------------------------------------

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
            end_time = datetime.now(
                timezone.utc
            )

        # ----------------------------------------------------
        # 1. Fetch Encounter.
        # ----------------------------------------------------

        encounter = self.repository.get(
            encounter_id
        )

        if encounter is None:
            raise RuntimeError(
                f"Encounter not found: "
                f"{encounter_id}"
            )

        if encounter["status"] == "CLOSED":
            raise RuntimeError(
                f"Encounter is already closed: "
                f"{encounter_id}"
            )

        # ----------------------------------------------------
        # 2. Persist closure.
        # ----------------------------------------------------

        self.repository.close(
            encounter_id=encounter_id,
            end_time=end_time,
            end_reason=end_reason,
            ended_by=ended_by,
            end_details=end_details,
        )

        # ----------------------------------------------------
        # 3. Create the historical Actual Encounter Span.
        #
        # The Starter Span is NOT ended here because it was
        # already completed at the 10-second point.
        #
        # Instead, TraceService creates:
        #
        # clinical.encounter
        #
        # with:
        #
        #     start = original Encounter start
        #     end   = actual Encounter closure
        #
        # and makes it a child of the Starter Span.
        # ----------------------------------------------------

        self.trace_service.end_encounter(
            encounter_id=encounter_id,
            start_time=encounter["start_time"],
            end_time=end_time,
            end_reason=end_reason,
            actor_id=ended_by,
            actor_role=actor_role,
            end_details=end_details,
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
        