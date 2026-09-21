from datetime import datetime, timezone
from typing import Any, Optional

from app.persistence.journals import JournalRepository
from app.services.trace_service import TraceService
from app.tracing.journal_registry import journal_span_registry
from app.persistence.episodes import EpisodeRepository


class JournalService:

    def __init__(
        self,
        repository=None,
        trace_service=None,
        episode_repository=None,
    ):
        self.repository = (
            repository or JournalRepository()
        )

        self.trace_service = (
            trace_service or TraceService()
        )

        self.episode_repository = (
            episode_repository or EpisodeRepository()
        )

    # ========================================================
    # EVENT
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
        episode_id: Optional[str] = None,
    ) -> dict[str, Any]:

        self._validate_content(content)

        if timestamp is None:
            timestamp = datetime.now(
                timezone.utc
            )

        self._validate_episode_parent(
            episode_id=episode_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
        )

        journal = self.repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=author_id,
            author_role=author_role,
            timestamp=timestamp,
            content=content,
            entry_type="EVENT",
            episode_id=episode_id,
        )

        try:

            self.trace_service.create_journal_event(
                journal_id=journal_id,
                patient_id=patient_id,
                encounter_id=encounter_id,
                author_id=author_id,
                author_role=author_role,
                content=content,
                timestamp=timestamp,
                episode_id=episode_id,
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
        episode_id: Optional[str] = None,
    ) -> dict[str, Any]:

        self._validate_content(content)

        if end_time < start_time:
            raise ValueError(
                "end_time cannot be before start_time"
            )

        self._validate_episode_parent(
            episode_id=episode_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
        )

        journal = self.repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=author_id,
            author_role=author_role,
            timestamp=start_time,
            content=content,
            entry_type="FIXED_ACTIVITY",
            episode_id=episode_id,
        )

        span = None

        try:

            span = (
                self.trace_service.start_journal_activity(
                    journal_id=journal_id,
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    author_id=author_id,
                    author_role=author_role,
                    content=content,
                    start_time=start_time,
                    episode_id=episode_id,
                )
            )

            if start_reason is not None:
                span.set_attribute(
                    "clinical.journal.start_reason",
                    start_reason,
                )

            self.trace_service.end_journal_activity(
                journal_id=journal_id,
                patient_id=patient_id,
                encounter_id=encounter_id,
                start_time=start_time,
                end_time=end_time,
                end_reason=end_reason,
                actor_id=author_id,
                actor_role=author_role,
                episode_id=episode_id,
            )

            return journal

        except Exception:

            if (
                span is not None
                and span.is_recording()
            ):
                span.end()

            journal_span_registry.remove(
                journal_id
            )

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
        start_time: Optional[datetime] = None,
        start_reason: Optional[str] = None,
        episode_id: Optional[str] = None,
    ) -> dict[str, Any]:

        self._validate_content(content)

        if start_time is None:
            start_time = datetime.now(
                timezone.utc
            )

        self._validate_episode_parent(
            episode_id=episode_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
        )

        journal = self.repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=author_id,
            author_role=author_role,
            timestamp=start_time,
            content=content,
            entry_type="ONGOING_ACTIVITY",
            episode_id=episode_id,
        )

        starter_span = None

        try:

            # ------------------------------------------------
            # Create the 10-second Journal Activity starter.
            # ------------------------------------------------

            starter_span = (
                self.trace_service.start_journal_activity(
                    journal_id=journal_id,
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    author_id=author_id,
                    author_role=author_role,
                    content=content,
                    start_time=start_time,
                    episode_id=episode_id,
                )
            )

            if start_reason is not None:
                starter_span.set_attribute(
                    "clinical.journal.start_reason",
                    start_reason,
                )

            # ------------------------------------------------
            # Finish the starter immediately.
            #
            # The registry retains it because its SpanContext
            # is needed later as the parent of the actual
            # Journal Activity span.
            # ------------------------------------------------

            self.trace_service.finish_journal_activity_starter(
                journal_id=journal_id,
                start_time=start_time,
            )

            return journal

        except Exception:

            if (
                starter_span is not None
                and starter_span.is_recording()
            ):
                starter_span.end()

            journal_span_registry.remove(
                journal_id
            )

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
        end_time: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> None:

        if end_time is None:
            end_time = datetime.now(
                timezone.utc
            )

        journal = self.repository.get(
            journal_id
        )

        if journal is None:
            raise ValueError(
                f"Journal not found: {journal_id}"
            )

        if journal["entry_type"] != "ONGOING_ACTIVITY":
            raise ValueError(
                f"Journal is not an ongoing activity: "
                f"{journal_id}"
            )

        if end_time < journal["timestamp"]:
            raise ValueError(
                "end_time cannot be before start_time"
            )

        span = journal_span_registry.get(
            journal_id
        )

        if span is None:
            raise RuntimeError(
                f"No active Journal span found "
                f"for {journal_id}"
            )

        self.trace_service.end_journal_activity(
            journal_id=journal_id,
            patient_id=journal["patient_id"],
            encounter_id=journal["encounter_id"],
            start_time=journal["timestamp"],
            end_time=end_time,
            end_reason=end_reason,
            actor_id=actor_id,
            actor_role=actor_role,
            episode_id=journal.get("episode_id"),
        )

        journal_span_registry.remove(
            journal_id
        )

    # ========================================================
    # GET JOURNAL
    # ========================================================

    def get(
        self,
        journal_id: str,
    ) -> Optional[dict[str, Any]]:

        return self.repository.get(
            journal_id
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_content(
        content: str,
    ) -> None:

        if content is None:
            raise ValueError(
                "content is required"
            )

        if not isinstance(content, str):
            raise ValueError(
                "content must be a string"
            )

        if not content.strip():
            raise ValueError(
                "content cannot be empty"
            )

    def _validate_episode_parent(
        self,
        episode_id: Optional[str],
        patient_id: str,
        encounter_id: str,
    ) -> None:

        if episode_id is None:
            return

        episode = self.episode_repository.get(
            episode_id
        )

        if episode is None:
            raise ValueError(
                f"Episode not found: {episode_id}"
            )

        if episode["patient_id"] != patient_id:
            raise ValueError(
                f"Episode {episode_id} "
                f"does not belong to patient {patient_id}"
            )

        if episode["encounter_id"] != encounter_id:
            raise ValueError(
                f"Episode {episode_id} "
                f"does not belong to encounter {encounter_id}"
            )

        if episode["status"] != "OPEN":
            raise ValueError(
                f"Episode {episode_id} is not open"
            )