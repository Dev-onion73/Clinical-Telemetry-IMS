from datetime import datetime, timezone, timedelta
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from app.tracing.context import context_from_ids
from app.tracing.provider import get_tracer
from app.tracing.registry import encounter_span_registry
from app.tracing.journal_registry import journal_span_registry
from app.tracing.episode_registry import episode_span_registry


def datetime_to_ns(
    value: Optional[datetime],
) -> Optional[int]:

    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return int(
        value.timestamp() * 1_000_000_000
    )


def force_trace_flush() -> None:
    """
    Force the configured OpenTelemetry SDK provider to flush
    completed spans to its configured span processors/exporters.

    This is important for the short Encounter Starter Span:
    the starter is deliberately ended immediately, so without
    a flush it may remain in the BatchSpanProcessor queue until
    its normal export interval.
    """

    provider = trace.get_tracer_provider()

    force_flush = getattr(
        provider,
        "force_flush",
        None,
    )

    if force_flush is not None:
        force_flush()


class TraceService:

    def __init__(self):
        self.tracer = get_tracer()

    # ========================================================
    # ENCOUNTER
    # ========================================================

    def start_encounter(
        self,
        encounter_id: str,
        patient_id: str,
        encounter_type: str,
        start_reason: str,
        actor_id: str,
        actor_role: str,
        start_details: Optional[str] = None,
        start_time: Optional[datetime] = None,
    ) -> Span:

        if start_time is None:
            start_time = datetime.now(timezone.utc)

        # ----------------------------------------------------
        # Create the Encounter Starter Span.
        #
        # This is a short-lived representation of the
        # Encounter initialization.
        #
        # It is NOT the actual Encounter duration.
        # ----------------------------------------------------

        span = self.tracer.start_span(
            name="clinical.encounter.starter",
            start_time=datetime_to_ns(
                start_time
            ),
        )

        span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        span.set_attribute(
            "clinical.encounter.type",
            encounter_type,
        )

        span.set_attribute(
            "clinical.encounter.start_reason",
            start_reason,
        )

        span.set_attribute(
            "clinical.actor.id",
            actor_id,
        )

        span.set_attribute(
            "clinical.actor.role",
            actor_role,
        )

        span.set_attribute(
            "clinical.encounter.representation",
            "starter",
        )

        span.set_attribute(
            "clinical.encounter.logical_start_time",
            start_time.isoformat(),
        )

        if start_details is not None:
            span.set_attribute(
                "clinical.encounter.start_details",
                start_details,
            )

        # ----------------------------------------------------
        # Exact logical start event.
        # ----------------------------------------------------

        span.add_event(
            name="clinical.encounter.started",
            timestamp=datetime_to_ns(
                start_time
            ),
            attributes={
                "clinical.encounter.id": encounter_id,
                "clinical.patient.id": patient_id,
                "clinical.actor.id": actor_id,
                "clinical.actor.role": actor_role,
            },
        )

        # ----------------------------------------------------
        # Register BEFORE finishing the starter.
        #
        # The registry intentionally retains this Span object
        # after it has ended because its SpanContext provides
        # the Encounter's trace lineage.
        # ----------------------------------------------------

        encounter_span_registry.register(
            encounter_id,
            span,
        )

        return span

    def finish_encounter_starter(
        self,
        encounter_id: str,
        start_time: datetime,
    ) -> None:

        starter_span = encounter_span_registry.get(
            encounter_id
        )

        if starter_span is None:
            raise RuntimeError(
                f"No Encounter starter span found "
                f"for {encounter_id}"
            )

        # ----------------------------------------------------
        # The starter is represented as exactly 10 seconds.
        #
        # We deliberately do NOT sleep for ten seconds.
        # Instead, we provide the historical end timestamp.
        # ----------------------------------------------------

        starter_end_time = (
            start_time
            + timedelta(seconds=10)
        )

        starter_span.end(
            end_time=datetime_to_ns(
                starter_end_time
            )
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # BatchSpanProcessor normally exports asynchronously.
        # Force a flush here so the Starter Span is visible
        # independently of Encounter closure.
        # ----------------------------------------------------

        force_trace_flush()

        # ----------------------------------------------------
        # DO NOT remove the starter from the registry.
        #
        # Its SpanContext remains the parent context for:
        #
        #   - Episodes
        #   - Encounter-level Journal Events
        #   - Encounter-level Journal Activities
        #
        # Even though the starter itself has already ended.
        # ----------------------------------------------------

    def end_encounter(
        self,
        encounter_id: str,
        start_time: datetime,
        end_time: datetime,
        end_reason: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        end_details: Optional[str] = None,
    ) -> None:

        starter_span = encounter_span_registry.get(
            encounter_id
        )

        if starter_span is None:
            raise RuntimeError(
                f"No Encounter trace context found "
                f"for {encounter_id}"
            )

        # ----------------------------------------------------
        # Create the Actual Encounter Span.
        #
        # This Span is created at closure time, but receives
        # the original Encounter start timestamp.
        #
        # Its parent is the already-ended Starter Span.
        # ----------------------------------------------------

        actual_span = self.start_child_span(
            name="clinical.encounter",
            parent_span=starter_span,
            start_time=start_time,
        )

        actual_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        actual_span.set_attribute(
            "clinical.encounter.actual",
            True,
        )

        actual_span.set_attribute(
            "clinical.encounter.representation",
            "actual",
        )

        actual_span.set_attribute(
            "clinical.encounter.logical_start_time",
            start_time.isoformat(),
        )

        actual_span.set_attribute(
            "clinical.encounter.logical_end_time",
            end_time.isoformat(),
        )

        if end_reason is not None:
            actual_span.set_attribute(
                "clinical.encounter.end_reason",
                end_reason,
            )

        if actor_id is not None:
            actual_span.set_attribute(
                "clinical.encounter.end_actor.id",
                actor_id,
            )

        if actor_role is not None:
            actual_span.set_attribute(
                "clinical.encounter.end_actor.role",
                actor_role,
            )

        if end_details is not None:
            actual_span.set_attribute(
                "clinical.encounter.end_details",
                end_details,
            )

        # ----------------------------------------------------
        # Exact logical end event.
        # ----------------------------------------------------

        actual_span.add_event(
            name="clinical.encounter.ended",
            timestamp=datetime_to_ns(
                end_time
            ),
            attributes={
                "clinical.encounter.id": encounter_id,
            },
        )

        # ----------------------------------------------------
        # Complete the historical Actual Encounter Span.
        # ----------------------------------------------------

        actual_span.end(
            end_time=datetime_to_ns(
                end_time
            )
        )

        # ----------------------------------------------------
        # Force immediate export of the Actual Encounter Span.
        # ----------------------------------------------------

        force_trace_flush()

        # ----------------------------------------------------
        # Encounter is now completely finished.
        # ----------------------------------------------------

        encounter_span_registry.remove(
            encounter_id
        )

    # ========================================================
    # GENERIC CHILD SPAN
    # ========================================================

    def start_child_span(
        self,
        name: str,
        parent_span: Span,
        start_time: Optional[datetime] = None,
    ) -> Span:

        parent_context = (
            trace.set_span_in_context(
                parent_span
            )
        )

        return self.tracer.start_span(
            name=name,
            context=parent_context,
            start_time=datetime_to_ns(
                start_time
            ),
        )

    def start_child_span_from_context(
        self,
        name: str,
        parent_trace_id: str,
        parent_span_id: str,
        start_time: Optional[datetime] = None,
    ) -> Span:

        parent_context = context_from_ids(
            parent_trace_id,
            parent_span_id,
        )

        return self.tracer.start_span(
            name=name,
            context=parent_context,
            start_time=datetime_to_ns(
                start_time
            ),
        )

     # ========================================================
    # EPISODE
    # ========================================================

    def start_episode(
        self,
        episode_id: str,
        patient_id: str,
        encounter_id: str,
        initiated_by: str,
        initiation_reason: str,
        source_journal_id: str,
        start_time: Optional[datetime] = None,
    ) -> Span:

        if start_time is None:
            start_time = datetime.now(timezone.utc)

        encounter_span = encounter_span_registry.get(
            encounter_id
        )

        if encounter_span is None:
            raise RuntimeError(
                f"No Encounter trace context found "
                f"for {encounter_id}"
            )

        episode_span = self.start_child_span(
            name="clinical.episode.starter",
            parent_span=encounter_span,
            start_time=start_time,
        )

        episode_span.set_attribute(
            "clinical.episode.id",
            episode_id,
        )

        episode_span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        episode_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        episode_span.set_attribute(
            "clinical.episode.initiated_by",
            initiated_by,
        )

        episode_span.set_attribute(
            "clinical.episode.initiation_reason",
            initiation_reason,
        )

        episode_span.set_attribute(
            "clinical.episode.source_journal_id",
            source_journal_id,
        )

        episode_span.set_attribute(
            "clinical.episode.representation",
            "starter",
        )

        episode_span.set_attribute(
            "clinical.episode.logical_start_time",
            start_time.isoformat(),
        )

        episode_span.add_event(
            name="clinical.episode.started",
            timestamp=datetime_to_ns(start_time),
            attributes={
                "clinical.episode.id": episode_id,
                "clinical.patient.id": patient_id,
                "clinical.encounter.id": encounter_id,
                "clinical.actor.id": initiated_by,
            },
        )

        episode_span_registry.register(
            episode_id,
            episode_span,
        )

        return episode_span

    def finish_episode_starter(
        self,
        episode_id: str,
        start_time: datetime,
    ) -> None:

        episode_span = episode_span_registry.get(
            episode_id
        )

        if episode_span is None:
            raise RuntimeError(
                f"No Episode starter span found "
                f"for {episode_id}"
            )

        starter_end_time = (
            start_time + timedelta(seconds=10)
        )

        episode_span.end(
            end_time=datetime_to_ns(
                starter_end_time
            )
        )

        force_trace_flush()

    def end_episode(
        self,
        episode_id: str,
        patient_id: str,
        encounter_id: str,
        start_time: datetime,
        end_time: datetime,
        closure_by: Optional[str] = None,
    ) -> None:

        episode_starter = episode_span_registry.get(
            episode_id
        )

        if episode_starter is None:
            raise RuntimeError(
                f"No Episode trace context found "
                f"for {episode_id}"
            )

        actual_span = self.start_child_span(
            name="clinical.episode",
            parent_span=episode_starter,
            start_time=start_time,
        )

        actual_span.set_attribute(
            "clinical.episode.id",
            episode_id,
        )

        actual_span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        actual_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        actual_span.set_attribute(
            "clinical.episode.actual",
            True,
        )

        actual_span.set_attribute(
            "clinical.episode.representation",
            "actual",
        )

        actual_span.set_attribute(
            "clinical.episode.logical_start_time",
            start_time.isoformat(),
        )

        actual_span.set_attribute(
            "clinical.episode.logical_end_time",
            end_time.isoformat(),
        )

        if closure_by is not None:
            actual_span.set_attribute(
                "clinical.episode.closure_by",
                closure_by,
            )

        end_attributes = {
            "clinical.episode.id": episode_id,
        }

        if closure_by is not None:
            end_attributes[
                "clinical.actor.id"
            ] = closure_by

        actual_span.add_event(
            name="clinical.episode.ended",
            timestamp=datetime_to_ns(end_time),
            attributes=end_attributes,
        )

        actual_span.end(
            end_time=datetime_to_ns(
                end_time
            )
        )

        force_trace_flush()

        episode_span_registry.remove(
            episode_id
        )
    # ========================================================
    # JOURNAL PARENT RESOLUTION
    # ========================================================

    def _resolve_journal_parent(
        self,
        encounter_id: str,
        episode_id: Optional[str] = None,
    ) -> Span:

        # ----------------------------------------------------
        # Episode-aware Journal
        # ----------------------------------------------------

        if episode_id is not None:

            episode_span = (
                episode_span_registry.get(
                    episode_id
                )
            )

            if episode_span is None:
                raise RuntimeError(
                    f"No active Episode span found "
                    f"for {episode_id}"
                )

            return episode_span

        # ----------------------------------------------------
        # Encounter-level Journal
        # ----------------------------------------------------

        encounter_span = (
            encounter_span_registry.get(
                encounter_id
            )
        )

        if encounter_span is None:
            raise RuntimeError(
                f"No active Encounter span found "
                f"for {encounter_id}"
            )

        return encounter_span

    # ========================================================
    # JOURNAL EVENT
    # ========================================================

    def create_journal_event(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        content: str,
        timestamp: datetime,
        episode_id: Optional[str] = None,
    ) -> None:

        parent_span = (
            self._resolve_journal_parent(
                encounter_id=encounter_id,
                episode_id=episode_id,
            )
        )

        parent_span.add_event(
            name="clinical.journal.event",
            timestamp=datetime_to_ns(
                timestamp
            ),
            attributes={
                "clinical.journal.id": journal_id,
                "clinical.patient.id": patient_id,
                "clinical.actor.id": author_id,
                "clinical.actor.role": author_role,
                "clinical.journal.content": content,
            },
        )

        if episode_id is not None:
            parent_span.set_attribute(
                "clinical.episode.journal.id",
                journal_id,
            )

    # ========================================================
    # JOURNAL ACTIVITY
    # ========================================================

    def start_journal_activity(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        content: str,
        start_time: Optional[datetime] = None,
        episode_id: Optional[str] = None,
    ) -> Span:

        parent_span = (
            self._resolve_journal_parent(
                encounter_id=encounter_id,
                episode_id=episode_id,
            )
        )

        span = self.start_child_span(
            name="clinical.journal.activity",
            parent_span=parent_span,
            start_time=start_time,
        )

        span.set_attribute(
            "clinical.journal.id",
            journal_id,
        )

        span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        span.set_attribute(
            "clinical.actor.id",
            author_id,
        )

        span.set_attribute(
            "clinical.actor.role",
            author_role,
        )

        span.set_attribute(
            "clinical.journal.content",
            content,
        )

        if episode_id is not None:
            span.set_attribute(
                "clinical.episode.id",
                episode_id,
            )

        # Keep the live Journal span available until
        # end_journal_activity() explicitly closes it.
        journal_span_registry.register(
            journal_id,
            span,
        )

        return span

    # ========================================================
    # END JOURNAL ACTIVITY
    # ========================================================

    def end_journal_activity(
        self,
        journal_id: str,
        end_time: datetime,
        end_reason: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> None:

        span = journal_span_registry.get(
            journal_id
        )

        if span is None:
            raise RuntimeError(
                f"No active Journal span found "
                f"for {journal_id}"
            )

        if end_reason is not None:
            span.set_attribute(
                "clinical.journal.end_reason",
                end_reason,
            )

        if actor_id is not None:
            span.set_attribute(
                "clinical.journal.end_actor.id",
                actor_id,
            )

        if actor_role is not None:
            span.set_attribute(
                "clinical.journal.end_actor.role",
                actor_role,
            )

        span.end(
            end_time=datetime_to_ns(
                end_time
            )
        )

        journal_span_registry.remove(
            journal_id
        )