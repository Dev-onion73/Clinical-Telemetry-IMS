from datetime import datetime, timezone
from typing import Any, Optional

from app.persistence.episodes import EpisodeRepository
from app.persistence.journals import JournalRepository
from app.services.trace_service import TraceService
from app.tracing.episode_registry import episode_span_registry


class EpisodeService:

    def __init__(
        self,
        episode_repository=None,
        journal_repository=None,
        trace_service=None,
    ):
        self.episode_repository = (
            episode_repository or EpisodeRepository()
        )

        self.journal_repository = (
            journal_repository or JournalRepository()
        )

        self.trace_service = (
            trace_service or TraceService()
        )

    # ---------------------------------------------------------
    # START EPISODE FROM JOURNAL
    # ---------------------------------------------------------

    def start_from_journal(
        self,
        episode_id: str,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        initiated_by: str,
        initiation_reason: str,
        author_role: str,
        content: str,
        start_time: Optional[datetime] = None,
    ) -> dict[str, Any]:

        self._validate_required(
            episode_id,
            "episode_id",
        )

        self._validate_required(
            journal_id,
            "journal_id",
        )

        self._validate_required(
            patient_id,
            "patient_id",
        )

        self._validate_required(
            encounter_id,
            "encounter_id",
        )

        self._validate_required(
            initiated_by,
            "initiated_by",
        )

        self._validate_required(
            initiation_reason,
            "initiation_reason",
        )

        self._validate_required(
            content,
            "content",
        )

        if start_time is None:
            start_time = datetime.now(timezone.utc)

        # -----------------------------------------------------
        # 1. Ensure Journal ID is not already in use
        # -----------------------------------------------------

        existing_journal = self.journal_repository.get(
            journal_id
        )

        if existing_journal is not None:
            raise ValueError(
                f"Journal already exists: {journal_id}"
            )

        # -----------------------------------------------------
        # 2. Ensure Episode ID is not already in use
        # -----------------------------------------------------

        existing_episode = self.episode_repository.get(
            episode_id
        )

        if existing_episode is not None:
            raise ValueError(
                f"Episode already exists: {episode_id}"
            )

        # -----------------------------------------------------
        # 3. Create originating Journal
        #
        # At this point episode_id is intentionally NULL.
        #
        # This avoids the circular FK dependency:
        #
        # journals.episode_id
        #       ↓
        # episodes.source_journal_id
        #       ↓
        # journals.journal_id
        # -----------------------------------------------------

        journal = self.journal_repository.create(
            journal_id=journal_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            author_id=initiated_by,
            author_role=author_role,
            timestamp=start_time,
            content=content,
            entry_type="EPISODE_START",
            episode_id=None,
        )

        episode = None
        episode_span = None

        try:

            # -------------------------------------------------
            # 4. Create Episode
            # -------------------------------------------------

            episode = self.episode_repository.create(
                episode_id=episode_id,
                patient_id=patient_id,
                encounter_id=encounter_id,
                initiated_by=initiated_by,
                initiation_reason=initiation_reason,
                start_time=start_time,
                source_journal_id=journal_id,
            )

            # -------------------------------------------------
            # 5. Attach Episode identity to originating Journal
            # -------------------------------------------------

            self.journal_repository.update_episode_identity(
                journal_id=journal_id,
                episode_id=episode_id,
            )

            # -------------------------------------------------
            # 6. Start Episode trace span
            #
            # Parent:
            #     clinical.encounter
            #
            # Child:
            #     clinical.episode
            # -------------------------------------------------

            episode_span = self.trace_service.start_episode(
                episode_id=episode_id,
                patient_id=patient_id,
                encounter_id=encounter_id,
                initiated_by=initiated_by,
                initiation_reason=initiation_reason,
                source_journal_id=journal_id,
                start_time=start_time,
            )

            # -------------------------------------------------
            # 7. Persist trace identity
            # -------------------------------------------------

            span_context = episode_span.get_span_context()

            trace_id = format(
                span_context.trace_id,
                "032x",
            )

            self.episode_repository.update_trace_identity(
                episode_id=episode_id,
                trace_id=trace_id,
            )

            # -------------------------------------------------
            # 8. Return fresh persisted Episode
            # -------------------------------------------------

            result = self.episode_repository.get(
                episode_id
            )

            if result is None:
                raise RuntimeError(
                    "Episode disappeared after creation"
                )

            return result

        except Exception:

            # -------------------------------------------------
            # Compensation
            # -------------------------------------------------

            if episode_span is not None:
                if episode_span.is_recording():
                    episode_span.end()

                episode_span_registry.remove(
                    episode_id
                )

            if episode is not None:
                self.episode_repository.delete(
                    episode_id
                )

            self.journal_repository.delete(
                journal_id
            )

            raise

    # ---------------------------------------------------------
    # CLOSE EPISODE
    # ---------------------------------------------------------

    def close(
        self,
        episode_id: str,
        closure_by: str,
        end_time: Optional[datetime] = None,
    ) -> dict[str, Any]:

        self._validate_required(
            episode_id,
            "episode_id",
        )

        self._validate_required(
            closure_by,
            "closure_by",
        )

        if end_time is None:
            end_time = datetime.now(timezone.utc)

        episode = self.episode_repository.get(
            episode_id
        )

        if episode is None:
            raise ValueError(
                f"Episode not found: {episode_id}"
            )

        if episode["status"] != "OPEN":
            raise ValueError(
                f"Episode is already closed: {episode_id}"
            )

        if end_time < episode["start_time"]:
            raise ValueError(
                "Episode end_time cannot be before start_time"
            )

        # -----------------------------------------------------
        # Close database lifecycle
        # -----------------------------------------------------

        self.episode_repository.close(
            episode_id=episode_id,
            end_time=end_time,
            closure_by=closure_by,
        )

        # -----------------------------------------------------
        # End trace span
        # -----------------------------------------------------

        self.trace_service.end_episode(
            episode_id=episode_id,
            end_time=end_time,
            closure_by=closure_by,
        )

        # -----------------------------------------------------
        # Return persisted state
        # -----------------------------------------------------

        result = self.episode_repository.get(
            episode_id
        )

        if result is None:
            raise RuntimeError(
                "Episode disappeared after closure"
            )

        return result

    # ---------------------------------------------------------
    # GET EPISODE
    # ---------------------------------------------------------

    def get(
        self,
        episode_id: str,
    ) -> Optional[dict[str, Any]]:

        return self.episode_repository.get(
            episode_id
        )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    @staticmethod
    def _validate_required(
        value: Optional[str],
        field_name: str,
    ) -> None:

        if value is None:
            raise ValueError(
                f"{field_name} is required"
            )

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} cannot be empty"
            )