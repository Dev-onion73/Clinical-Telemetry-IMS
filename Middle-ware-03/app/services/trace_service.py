from datetime import datetime, timezone
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from app.tracing.context import context_from_ids
from app.tracing.provider import get_tracer
from app.tracing.registry import encounter_span_registry
from app.tracing.episode_registry import episode_span_registry

def datetime_to_ns(
    value: Optional[datetime],
) -> Optional[int]:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return int(value.timestamp() * 1_000_000_000)


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

        span = self.tracer.start_span(
            name="clinical.encounter",
            start_time=datetime_to_ns(start_time),
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

        if start_details is not None:
            span.set_attribute(
                "clinical.encounter.start_details",
                start_details,
            )

        encounter_span_registry.register(
            encounter_id,
            span,
        )

        return span

    def end_encounter(
        self,
        encounter_id: str,
        end_time: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        end_details: Optional[str] = None,
    ) -> None:

        span = encounter_span_registry.get(
            encounter_id
        )

        if span is None:
            raise RuntimeError(
                f"No active Encounter span found for "
                f"{encounter_id}"
            )

        if end_reason is not None:
            span.set_attribute(
                "clinical.encounter.end_reason",
                end_reason,
            )

        if actor_id is not None:
            span.set_attribute(
                "clinical.encounter.end_actor.id",
                actor_id,
            )

        if actor_role is not None:
            span.set_attribute(
                "clinical.encounter.end_actor.role",
                actor_role,
            )

        if end_details is not None:
            span.set_attribute(
                "clinical.encounter.end_details",
                end_details,
            )

        span.end(
            end_time=datetime_to_ns(end_time)
        )

        encounter_span_registry.remove(
            encounter_id
        )

    # ========================================================
    # CHILD SPAN
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
            start_time=datetime_to_ns(start_time),
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
            start_time=datetime_to_ns(start_time),
        )

    # ========================================================
    # JOURNAL EVENT
    # ========================================================

    def create_journal_event(
        self,
        encounter_id: str,
        journal_id: str,
        patient_id: str,
        author_id: str,
        author_role: str,
        content: str,
        timestamp: Optional[datetime] = None,
    ) -> None:

        encounter_span = (
            encounter_span_registry.get(
                encounter_id
            )
        )

        if encounter_span is None:
            raise RuntimeError(
                f"No active Encounter span found for "
                f"{encounter_id}"
            )

        encounter_span.add_event(
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

    # ========================================================
    # JOURNAL ACTIVITY
    # ========================================================

    def start_journal_activity(
        self,
        encounter_id: str,
        journal_id: str,
        patient_id: str,
        author_id: str,
        author_role: str,
        content: str,
        start_time: Optional[datetime] = None,
    ) -> Span:

        encounter_span = (
            encounter_span_registry.get(
                encounter_id
            )
        )

        if encounter_span is None:
            raise RuntimeError(
                f"No active Encounter span found for "
                f"{encounter_id}"
            )

        span = self.start_child_span(
            name="clinical.journal.activity",
            parent_span=encounter_span,
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

        return span

    def end_journal_activity(
        self,
        span: Span,
        end_time: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> None:

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
            end_time=datetime_to_ns(end_time)
        )

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

        encounter_span = encounter_span_registry.get(
            encounter_id
        )

        if encounter_span is None:
            raise RuntimeError(
                f"No active Encounter span found for {encounter_id}"
            )

        span = self.start_child_span(
            name="clinical.episode",
            parent_span=encounter_span,
            start_time=start_time,
        )

        span.set_attribute(
            "clinical.episode.id",
            episode_id,
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
            "clinical.episode.initiated_by",
            initiated_by,
        )

        span.set_attribute(
            "clinical.episode.initiation_reason",
            initiation_reason,
        )

        span.set_attribute(
            "clinical.episode.source_journal_id",
            source_journal_id,
        )

        episode_span_registry.register(
            episode_id,
            span,
        )

        return span

    def end_episode(
        self,
        episode_id: str,
        end_time: datetime,
        closure_by: Optional[str] = None,
    ) -> None:

        span = episode_span_registry.get(
            episode_id
        )

        if span is None:
            raise RuntimeError(
                f"No active Episode span found for {episode_id}"
            )

        if closure_by is not None:
            span.set_attribute(
                "clinical.episode.closure_by",
                closure_by,
            )

        span.end(
            end_time=datetime_to_ns(end_time)
        )

        episode_span_registry.remove(
            episode_id
        )