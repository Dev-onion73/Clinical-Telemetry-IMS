from datetime import datetime, timezone
from typing import Any, Optional

from app.persistence.journals import JournalRepository
from app.services.trace_service import TraceService
from app.tracing.journal_registry import (
    journal_span_registry,
)


class JournalService:

    def __init__(
        self,
        repository: Optional[JournalRepository] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.repository = (
            repository
            or JournalRepository()
        )

        self.trace_service = (
            trace_service
            or TraceService()
        )

    # ========================================================
    # JOURNAL EVENT
    # ========================================================

    def create_event(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        content: str,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Any]:

        if not content.strip():
            raise ValueError(
                "Journal content is required"
            )

        if timestamp is None:
            timestamp = datetime.now(
                timezone.utc
            )

        journal = self.repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=author_id,
            author_role=author_role,
            timestamp=timestamp,
            content=content,
        )

        try:

            self.trace_service.create_journal_event(
                encounter_id=encounter_id,
                journal_id=journal_id,
                patient_id=patient_id,
                author_id=author_id,
                author_role=author_role,
                content=content,
                timestamp=timestamp,
            )

            return journal

        except Exception:

            self.repository.delete(
                journal_id
            )

            raise

    # ========================================================
    # FIXED ACTIVITY
    # ========================================================

    def create_fixed_activity(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        content: str,
        start_time: datetime,
        end_time: datetime,
        start_reason: Optional[str] = None,
        end_reason: Optional[str] = None,
    ) -> dict[str, Any]:

        if not content.strip():
            raise ValueError(
                "Journal content is required"
            )

        if end_time < start_time:
            raise ValueError(
                "end_time cannot precede start_time"
            )

        journal = self.repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=author_id,
            author_role=author_role,
            timestamp=start_time,
            content=content,
        )

        span = None

        try:

            span = (
                self.trace_service
                .start_journal_activity(
                    encounter_id=encounter_id,
                    journal_id=journal_id,
                    patient_id=patient_id,
                    author_id=author_id,
                    author_role=author_role,
                    content=content,
                    start_time=start_time,
                )
            )

            if start_reason is not None:
                span.set_attribute(
                    "clinical.journal.start_reason",
                    start_reason,
                )

            self.trace_service.end_journal_activity(
                span=span,
                end_time=end_time,
                end_reason=end_reason,
                actor_id=author_id,
                actor_role=author_role,
            )

            return journal

        except Exception:

            if (
                span is not None
                and span.is_recording()
            ):
                span.end()

            self.repository.delete(
                journal_id
            )

            raise

    # ========================================================
    # ONGOING ACTIVITY
    # ========================================================

    def start_ongoing_activity(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        content: str,
        start_reason: Optional[str] = None,
        start_time: Optional[datetime] = None,
    ) -> dict[str, Any]:

        if not content.strip():
            raise ValueError(
                "Journal content is required"
            )

        if start_time is None:
            start_time = datetime.now(
                timezone.utc
            )

        journal = self.repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=author_id,
            author_role=author_role,
            timestamp=start_time,
            content=content,
        )

        span = None

        try:

            span = (
                self.trace_service
                .start_journal_activity(
                    encounter_id=encounter_id,
                    journal_id=journal_id,
                    patient_id=patient_id,
                    author_id=author_id,
                    author_role=author_role,
                    content=content,
                    start_time=start_time,
                )
            )

            if start_reason is not None:
                span.set_attribute(
                    "clinical.journal.start_reason",
                    start_reason,
                )

            journal_span_registry.register(
                journal_id,
                span,
            )

            return journal

        except Exception:

            if (
                span is not None
                and span.is_recording()
            ):
                span.end()

            self.repository.delete(
                journal_id
            )

            raise

    # ========================================================
    # END ONGOING ACTIVITY
    # ========================================================

    def end_ongoing_activity(
        self,
        journal_id: str,
        end_reason: Optional[str] = None,
        ended_by: Optional[str] = None,
        ended_by_role: Optional[str] = None,
        end_time: Optional[datetime] = None,
    ) -> None:

        if end_time is None:
            end_time = datetime.now(
                timezone.utc
            )

        span = journal_span_registry.get(
            journal_id
        )

        if span is None:
            raise RuntimeError(
                f"No active Journal span found: "
                f"{journal_id}"
            )

        self.trace_service.end_journal_activity(
            span=span,
            end_time=end_time,
            end_reason=end_reason,
            actor_id=ended_by,
            actor_role=ended_by_role,
        )

        journal_span_registry.remove(
            journal_id
        )