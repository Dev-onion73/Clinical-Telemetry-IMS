from datetime import datetime, timezone
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from app.tracing.context import context_from_ids
from app.tracing.provider import get_tracer
from app.tracing.registry import encounter_span_registry


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

    # ================================================================
    # ENCOUNTER
    # ================================================================

    def start_encounter(
        self,
        encounter_id: str,
        patient_id: str,
        encounter_type: str,
        start_reason: str,
        actor_id: str,
        actor_role: str,
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

        # Keep the actual recording Encounter span alive
        # while the Encounter remains open.
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

        span.end(
            end_time=datetime_to_ns(end_time)
        )

        # The Span is no longer needed once it has ended.
        encounter_span_registry.remove(
            encounter_id
        )

    # ================================================================
    # ENCOUNTER CONTEXT
    # ================================================================

    def get_encounter_context(
        self,
        encounter_id: str,
    ):
        span = encounter_span_registry.get(
            encounter_id
        )

        if span is None:
            raise RuntimeError(
                f"No active Encounter span found for "
                f"{encounter_id}"
            )

        return trace.set_span_in_context(
            span
        )

    # ================================================================
    # CHILD SPAN
    # ================================================================

    def start_child_span(
        self,
        name: str,
        parent_span: Span,
        start_time: Optional[datetime] = None,
    ) -> Span:

        parent_context = trace.set_span_in_context(
            parent_span
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