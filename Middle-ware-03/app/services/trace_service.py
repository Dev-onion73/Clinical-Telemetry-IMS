
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span

from app.tracing.registry import encounter_span_registry
from app.tracing.episode_registry import episode_span_registry
from app.tracing.journal_registry import journal_span_registry
from app.tracing.alert_registry import alert_span_registry


# ============================================================
# HELPERS
# ============================================================

def datetime_to_ns(
    value: datetime,
) -> int:
    """
    Convert a datetime into an OpenTelemetry nanosecond
    timestamp.

    Naive datetimes are treated as UTC.
    """

    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return int(
        value.timestamp()
        * 1_000_000_000
    )


def force_trace_flush() -> None:
    """
    Force the configured OpenTelemetry tracer provider
    to export completed spans immediately when supported.
    """

    provider = trace.get_tracer_provider()

    force_flush = getattr(
        provider,
        "force_flush",
        None,
    )

    if force_flush is not None:
        force_flush()


# ============================================================
# TRACE SERVICE
# ============================================================

class TraceService:

    def __init__(
        self,
        tracer=None,
    ):
        self.tracer = (
            tracer
            or trace.get_tracer(
                "clinical-middleware"
            )
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

        if start_time is None:
            return self.tracer.start_span(
                name=name,
                context=parent_context,
            )

        return self.tracer.start_span(
            name=name,
            context=parent_context,
            start_time=datetime_to_ns(
                start_time
            ),
        )

    # ========================================================
    # ENCOUNTER
    # ========================================================

    def start_encounter(
        self,
        encounter_id: str,
        patient_id: str,
        encounter_type: str,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        start_reason: Optional[str] = None,
        start_details: Optional[str] = None,
        start_time: Optional[datetime] = None,
        started_by: Optional[str] = None,
        started_by_role: Optional[str] = None,
    ) -> Span:

        if start_time is None:
            start_time = datetime.now(
                timezone.utc
            )

        if actor_id is None:
            actor_id = started_by

        if actor_role is None:
            actor_role = started_by_role

        if start_reason is None:
            start_reason = start_details

        encounter_span = self.tracer.start_span(
            name="clinical.encounter.starter",
            start_time=datetime_to_ns(
                start_time
            ),
        )

        encounter_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        encounter_span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        encounter_span.set_attribute(
            "clinical.encounter.type",
            encounter_type,
        )

        if actor_id is not None:
            encounter_span.set_attribute(
                "clinical.encounter.actor_id",
                actor_id,
            )

        if actor_role is not None:
            encounter_span.set_attribute(
                "clinical.encounter.actor_role",
                actor_role,
            )

        if start_reason is not None:
            encounter_span.set_attribute(
                "clinical.encounter.start_reason",
                start_reason,
            )

        if start_details is not None:
            encounter_span.set_attribute(
                "clinical.encounter.start_details",
                start_details,
            )

        encounter_span.set_attribute(
            "clinical.encounter.actual",
            False,
        )

        encounter_span.set_attribute(
            "clinical.encounter.representation",
            "starter",
        )

        encounter_span.set_attribute(
            "clinical.encounter.logical_start_time",
            start_time.isoformat(),
        )

        event_attributes = {
            "clinical.encounter.id": encounter_id,
            "clinical.patient.id": patient_id,
        }

        if actor_id is not None:
            event_attributes[
                "clinical.actor.id"
            ] = actor_id

        if actor_role is not None:
            event_attributes[
                "clinical.actor.role"
            ] = actor_role

        if start_reason is not None:
            event_attributes[
                "clinical.encounter.start_reason"
            ] = start_reason

        if start_details is not None:
            event_attributes[
                "clinical.encounter.start_details"
            ] = start_details

        encounter_span.add_event(
            name="clinical.encounter.started",
            timestamp=datetime_to_ns(
                start_time
            ),
            attributes=event_attributes,
        )

        encounter_span_registry.register(
            encounter_id,
            encounter_span,
        )

        return encounter_span

    # ========================================================
    # FINISH ENCOUNTER STARTER
    # ========================================================

    def finish_encounter_starter(
        self,
        encounter_id: str,
        start_time: datetime,
    ) -> None:

        encounter_span = (
            encounter_span_registry.get(
                encounter_id
            )
        )

        if encounter_span is None:
            raise RuntimeError(
                f"No Encounter starter span found "
                f"for {encounter_id}"
            )

        starter_end_time = (
            start_time
            + timedelta(seconds=10)
        )

        encounter_span.end(
            end_time=datetime_to_ns(
                starter_end_time
            )
        )

        force_trace_flush()

    # ========================================================
    # END ENCOUNTER
    # ========================================================

    def end_encounter(
        self,
        encounter_id: str,
        patient_id: Optional[str] = None,
        encounter_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        closure_by: Optional[str] = None,
        closure_by_role: Optional[str] = None,
        end_reason: Optional[str] = None,
        end_details: Optional[str] = None,
    ) -> None:

        encounter_starter = (
            encounter_span_registry.get(
                encounter_id
            )
        )

        if encounter_starter is None:
            raise RuntimeError(
                f"No Encounter trace context found "
                f"for {encounter_id}"
            )

        starter_attributes = getattr(
            encounter_starter,
            "_attributes",
            None,
        )

        if starter_attributes is None:
            starter_attributes = {}

        if patient_id is None:
            patient_id = starter_attributes.get(
                "clinical.patient.id"
            )

        if encounter_type is None:
            encounter_type = starter_attributes.get(
                "clinical.encounter.type"
            )

        if patient_id is None:
            raise ValueError(
                f"patient_id could not be resolved "
                f"for Encounter {encounter_id}"
            )

        if encounter_type is None:
            raise ValueError(
                f"encounter_type could not be resolved "
                f"for Encounter {encounter_id}"
            )

        if start_time is None:

            logical_start = starter_attributes.get(
                "clinical.encounter.logical_start_time"
            )

            if logical_start is None:
                raise ValueError(
                    f"start_time could not be resolved "
                    f"for Encounter {encounter_id}"
                )

            start_time = datetime.fromisoformat(
                logical_start
            )

        if end_time is None:
            raise ValueError(
                f"end_time is required to end "
                f"Encounter {encounter_id}"
            )

        if end_time < start_time:
            raise ValueError(
                f"end_time cannot be earlier than "
                f"start_time for Encounter "
                f"{encounter_id}"
            )

        if actor_id is None:
            actor_id = closure_by

        if actor_role is None:
            actor_role = closure_by_role

        actual_span = self.start_child_span(
            name="clinical.encounter",
            parent_span=encounter_starter,
            start_time=start_time,
        )

        actual_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        actual_span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        actual_span.set_attribute(
            "clinical.encounter.type",
            encounter_type,
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

        if actor_id is not None:
            actual_span.set_attribute(
                "clinical.encounter.closure_by",
                actor_id,
            )

        if actor_role is not None:
            actual_span.set_attribute(
                "clinical.encounter.closure_by_role",
                actor_role,
            )

        if end_reason is not None:
            actual_span.set_attribute(
                "clinical.encounter.end_reason",
                end_reason,
            )

        if end_details is not None:
            actual_span.set_attribute(
                "clinical.encounter.end_details",
                end_details,
            )

        event_attributes = {
            "clinical.encounter.id": encounter_id,
            "clinical.patient.id": patient_id,
        }

        if actor_id is not None:
            event_attributes[
                "clinical.actor.id"
            ] = actor_id

        if actor_role is not None:
            event_attributes[
                "clinical.actor.role"
            ] = actor_role

        if end_reason is not None:
            event_attributes[
                "clinical.encounter.end_reason"
            ] = end_reason

        if end_details is not None:
            event_attributes[
                "clinical.encounter.end_details"
            ] = end_details

        actual_span.add_event(
            name="clinical.encounter.ended",
            timestamp=datetime_to_ns(
                end_time
            ),
            attributes=event_attributes,
        )

        actual_span.end(
            end_time=datetime_to_ns(
                end_time
            )
        )

        force_trace_flush()

        encounter_span_registry.remove(
            encounter_id
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
            start_time = datetime.now(
                timezone.utc
            )

        encounter_span = (
            encounter_span_registry.get(
                encounter_id
            )
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
            timestamp=datetime_to_ns(
                start_time
            ),
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

    # ========================================================
    # FINISH EPISODE STARTER
    # ========================================================

    def finish_episode_starter(
        self,
        episode_id: str,
        start_time: datetime,
    ) -> None:

        episode_span = (
            episode_span_registry.get(
                episode_id
            )
        )

        if episode_span is None:
            raise RuntimeError(
                f"No Episode starter span found "
                f"for {episode_id}"
            )

        starter_end_time = (
            start_time
            + timedelta(seconds=10)
        )

        episode_span.end(
            end_time=datetime_to_ns(
                starter_end_time
            )
        )

        force_trace_flush()

    # ========================================================
    # END EPISODE
    # ========================================================

    def end_episode(
        self,
        episode_id: str,
        patient_id: str,
        encounter_id: str,
        start_time: datetime,
        end_time: datetime,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        closure_by: Optional[str] = None,
        closure_by_role: Optional[str] = None,
    ) -> None:

        episode_starter = (
            episode_span_registry.get(
                episode_id
            )
        )

        if episode_starter is None:
            raise RuntimeError(
                f"No Episode trace context found "
                f"for {episode_id}"
            )

        if end_time < start_time:
            raise ValueError(
                f"end_time cannot be earlier than "
                f"start_time for Episode "
                f"{episode_id}"
            )

        if actor_id is None:
            actor_id = closure_by

        if actor_role is None:
            actor_role = closure_by_role

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

        if actor_id is not None:
            actual_span.set_attribute(
                "clinical.episode.closure_by",
                actor_id,
            )

        if actor_role is not None:
            actual_span.set_attribute(
                "clinical.episode.closure_by_role",
                actor_role,
            )

        event_attributes = {
            "clinical.episode.id": episode_id,
            "clinical.patient.id": patient_id,
            "clinical.encounter.id": encounter_id,
        }

        if actor_id is not None:
            event_attributes[
                "clinical.actor.id"
            ] = actor_id

        if actor_role is not None:
            event_attributes[
                "clinical.actor.role"
            ] = actor_role

        actual_span.add_event(
            name="clinical.episode.ended",
            timestamp=datetime_to_ns(
                end_time
            ),
            attributes=event_attributes,
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
    ) -> Span:

        parent_span = None

        if episode_id is not None:

            parent_span = (
                episode_span_registry.get(
                    episode_id
                )
            )

            if parent_span is None:
                raise RuntimeError(
                    f"No Episode trace context found "
                    f"for {episode_id}"
                )

        if parent_span is None:

            parent_span = (
                encounter_span_registry.get(
                    encounter_id
                )
            )

        if parent_span is None:
            raise RuntimeError(
                f"No Encounter trace context found "
                f"for {encounter_id}"
            )

        journal_span = self.start_child_span(
            name="clinical.journal.event",
            parent_span=parent_span,
            start_time=timestamp,
        )

        journal_span.set_attribute(
            "clinical.journal.id",
            journal_id,
        )

        journal_span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        journal_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        journal_span.set_attribute(
            "clinical.journal.author_id",
            author_id,
        )

        journal_span.set_attribute(
            "clinical.journal.author_role",
            author_role,
        )

        journal_span.set_attribute(
            "clinical.journal.entry_type",
            "EVENT",
        )

        journal_span.set_attribute(
            "clinical.journal.actual",
            True,
        )

        journal_span.set_attribute(
            "clinical.journal.representation",
            "actual",
        )

        if episode_id is not None:
            journal_span.set_attribute(
                "clinical.episode.id",
                episode_id,
            )

        journal_span.add_event(
            name="clinical.journal.event",
            timestamp=datetime_to_ns(
                timestamp
            ),
            attributes={
                "clinical.journal.id": journal_id,
                "clinical.journal.content": content,
            },
        )

        journal_span.end(
            end_time=datetime_to_ns(
                timestamp
            )
        )

        force_trace_flush()

        return journal_span

    # ========================================================
    # JOURNAL ACTIVITY STARTER
    # ========================================================

    def start_journal_activity(
        self,
        journal_id: str,
        patient_id: str,
        encounter_id: str,
        author_id: str,
        author_role: str,
        content: str,
        start_time: datetime,
        episode_id: Optional[str] = None,
    ) -> Span:

        parent_span = None

        if episode_id is not None:

            parent_span = (
                episode_span_registry.get(
                    episode_id
                )
            )

            if parent_span is None:
                raise RuntimeError(
                    f"No Episode trace context found "
                    f"for {episode_id}"
                )

        if parent_span is None:

            parent_span = (
                encounter_span_registry.get(
                    encounter_id
                )
            )

        if parent_span is None:
            raise RuntimeError(
                f"No Encounter trace context found "
                f"for {encounter_id}"
            )

        journal_span = self.start_child_span(
            name="clinical.journal.activity.starter",
            parent_span=parent_span,
            start_time=start_time,
        )

        journal_span.set_attribute(
            "clinical.journal.id",
            journal_id,
        )

        journal_span.set_attribute(
            "clinical.patient.id",
            patient_id,
        )

        journal_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        journal_span.set_attribute(
            "clinical.journal.author_id",
            author_id,
        )

        journal_span.set_attribute(
            "clinical.journal.author_role",
            author_role,
        )

        journal_span.set_attribute(
            "clinical.journal.entry_type",
            "ACTIVITY",
        )

        journal_span.set_attribute(
            "clinical.journal.representation",
            "starter",
        )

        journal_span.set_attribute(
            "clinical.journal.logical_start_time",
            start_time.isoformat(),
        )

        if episode_id is not None:
            journal_span.set_attribute(
                "clinical.episode.id",
                episode_id,
            )

        journal_span.add_event(
            name="clinical.journal.activity.started",
            timestamp=datetime_to_ns(
                start_time
            ),
            attributes={
                "clinical.journal.id": journal_id,
                "clinical.patient.id": patient_id,
                "clinical.encounter.id": encounter_id,
                "clinical.journal.author_id": author_id,
                "clinical.journal.author_role": author_role,
                "clinical.journal.content": content,
            },
        )

        journal_span_registry.register(
            journal_id,
            journal_span,
        )

        return journal_span

    # ========================================================
    # FINISH JOURNAL ACTIVITY STARTER
    # ========================================================

    def finish_journal_activity_starter(
        self,
        journal_id: str,
        start_time: datetime,
    ) -> None:

        journal_span = (
            journal_span_registry.get(
                journal_id
            )
        )

        if journal_span is None:
            raise RuntimeError(
                f"No Journal Activity starter span "
                f"found for {journal_id}"
            )

        starter_end_time = (
            start_time
            + timedelta(seconds=10)
        )

        journal_span.end(
            end_time=datetime_to_ns(
                starter_end_time
            )
        )

        force_trace_flush()

    # ========================================================
    # END JOURNAL ACTIVITY
    # ========================================================

    def end_journal_activity(
        self,
        journal_id: str,
        patient_id: Optional[str] = None,
        encounter_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        episode_id: Optional[str] = None,
        closure_by: Optional[str] = None,
        closure_by_role: Optional[str] = None,
    ) -> None:

        journal_starter = (
            journal_span_registry.get(
                journal_id
            )
        )

        if journal_starter is None:
            raise RuntimeError(
                f"No Journal Activity trace context "
                f"found for {journal_id}"
            )

        if actor_id is None:
            actor_id = closure_by

        if actor_role is None:
            actor_role = closure_by_role

        if patient_id is None:
            raise ValueError(
                f"patient_id is required to end "
                f"Journal Activity {journal_id}"
            )

        if encounter_id is None:
            raise ValueError(
                f"encounter_id is required to end "
                f"Journal Activity {journal_id}"
            )

        if start_time is None:
            raise ValueError(
                f"start_time is required to end "
                f"Journal Activity {journal_id}"
            )

        if end_time is None:
            raise ValueError(
                f"end_time is required to end "
                f"Journal Activity {journal_id}"
            )

        if end_time < start_time:
            raise ValueError(
                f"end_time cannot be earlier than "
                f"start_time for Journal Activity "
                f"{journal_id}"
            )

        actual_span = self.start_child_span(
            name="clinical.journal.activity",
            parent_span=journal_starter,
            start_time=start_time,
        )

        actual_span.set_attribute(
            "clinical.journal.id",
            journal_id,
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
            "clinical.journal.entry_type",
            "ACTIVITY",
        )

        actual_span.set_attribute(
            "clinical.journal.actual",
            True,
        )

        actual_span.set_attribute(
            "clinical.journal.representation",
            "actual",
        )

        actual_span.set_attribute(
            "clinical.journal.logical_start_time",
            start_time.isoformat(),
        )

        actual_span.set_attribute(
            "clinical.journal.logical_end_time",
            end_time.isoformat(),
        )

        if episode_id is not None:
            actual_span.set_attribute(
                "clinical.episode.id",
                episode_id,
            )

        if end_reason is not None:
            actual_span.set_attribute(
                "clinical.journal.end_reason",
                end_reason,
            )

        if actor_id is not None:
            actual_span.set_attribute(
                "clinical.journal.closure_actor_id",
                actor_id,
            )

        if actor_role is not None:
            actual_span.set_attribute(
                "clinical.journal.closure_actor_role",
                actor_role,
            )

        event_attributes = {
            "clinical.journal.id": journal_id,
            "clinical.patient.id": patient_id,
            "clinical.encounter.id": encounter_id,
        }

        if actor_id is not None:
            event_attributes[
                "clinical.actor.id"
            ] = actor_id

        if actor_role is not None:
            event_attributes[
                "clinical.actor.role"
            ] = actor_role

        if end_reason is not None:
            event_attributes[
                "clinical.journal.end_reason"
            ] = end_reason

        if episode_id is not None:
            event_attributes[
                "clinical.episode.id"
            ] = episode_id

        actual_span.add_event(
            name="clinical.journal.activity.ended",
            timestamp=datetime_to_ns(
                end_time
            ),
            attributes=event_attributes,
        )

        actual_span.end(
            end_time=datetime_to_ns(
                end_time
            )
        )

        force_trace_flush()

        journal_span_registry.remove(
            journal_id
        )

    # ========================================================
    # ALERT HELPERS
    # ========================================================

    @staticmethod
    def _alert_span_ids(
        span: Span,
    ) -> tuple[str, str]:

        context = span.get_span_context()

        return (
            format(
                context.trace_id,
                "032x",
            ),
            format(
                context.span_id,
                "016x",
            ),
        )

    @staticmethod
    def _apply_alert_attributes(
        span: Span,
        attributes: dict[str, Any] | None,
    ) -> None:

        if not attributes:
            return

        for key, value in attributes.items():

            if value is None:
                continue

            try:
                span.set_attribute(
                    key,
                    value,
                )

            except Exception as exc:
                print(
                    "[ALERT TRACE] WARNING: "
                    f"failed to set attribute "
                    f"{key!r}={value!r}: {exc}"
                )

    # ========================================================
    # ALERT THRESHOLD
    #
    # Hierarchy:
    #
    # clinical.encounter
    #     └── clinical.alert.threshold
    #             └── clinical.alert.resolution
    #
    # The threshold starts immediately when Grafana sends
    # "firing" and remains open until "resolved".
    # ========================================================

    def start_alert(
        self,
        fingerprint: str,
        encounter_id: str,
        patient_id: str | None,
        alert_name: str,
        starts_at: datetime,
        attributes: dict[str, Any] | None = None,
    ) -> Span:

        existing_span = (
            alert_span_registry.get(
                fingerprint
            )
        )

        if existing_span is not None:

            trace_id, span_id = (
                self._alert_span_ids(
                    existing_span
                )
            )

            print(
                "\n================ ALERT TRACE ================"
            )

            print(
                "[ALERT TRACE] DUPLICATE FIRING"
            )

            print(
                f"  fingerprint : {fingerprint}"
            )

            print(
                f"  trace_id    : {trace_id}"
            )

            print(
                f"  span_id     : {span_id}"
            )

            print(
                "  action      : existing threshold reused"
            )

            print(
                "=============================================\n"
            )

            return existing_span

        encounter_span = (
            encounter_span_registry.get(
                encounter_id
            )
        )

        if encounter_span is None:
            raise RuntimeError(
                "No active encounter span found "
                f"for encounter_id={encounter_id!r}"
            )

        (
            encounter_trace_id,
            encounter_span_id,
        ) = self._alert_span_ids(
            encounter_span
        )

        threshold_span = (
            self.start_child_span(
                name="clinical.alert.threshold",
                parent_span=encounter_span,
                start_time=starts_at,
            )
        )

        threshold_span.set_attribute(
            "clinical.alert.fingerprint",
            fingerprint,
        )

        threshold_span.set_attribute(
            "clinical.alert.name",
            alert_name,
        )

        threshold_span.set_attribute(
            "clinical.alert.status",
            "firing",
        )

        threshold_span.set_attribute(
            "clinical.alert.phase",
            "threshold",
        )

        threshold_span.set_attribute(
            "clinical.alert.actual",
            True,
        )

        threshold_span.set_attribute(
            "clinical.alert.representation",
            "threshold",
        )

        threshold_span.set_attribute(
            "clinical.encounter.id",
            encounter_id,
        )

        threshold_span.set_attribute(
            "clinical.alert.starts_at",
            starts_at.isoformat(),
        )

        if patient_id:
            threshold_span.set_attribute(
                "clinical.patient.id",
                patient_id,
            )

        self._apply_alert_attributes(
            threshold_span,
            attributes,
        )

        event_attributes = {
            "clinical.alert.fingerprint":
                fingerprint,
            "clinical.alert.name":
                alert_name,
            "clinical.encounter.id":
                encounter_id,
        }

        if patient_id:
            event_attributes[
                "clinical.patient.id"
            ] = patient_id

        threshold_span.add_event(
            name="clinical.alert.firing",
            timestamp=datetime_to_ns(
                starts_at
            ),
            attributes=event_attributes,
        )

        alert_span_registry.register(
            fingerprint=fingerprint,
            span=threshold_span,
        )

        (
            trace_id,
            threshold_span_id,
        ) = self._alert_span_ids(
            threshold_span
        )

        print(
            "\n================ ALERT TRACE ================"
        )

        print(
            "[ALERT TRACE] FIRING"
        )

        print(
            f"  fingerprint : {fingerprint}"
        )

        print(
            f"  alert       : {alert_name}"
        )

        print(
            f"  encounter   : {encounter_id}"
        )

        print(
            f"  patient     : {patient_id}"
        )

        print(
            f"  starts_at   : {starts_at.isoformat()}"
        )

        print()

        print(
            "  ENCOUNTER PARENT"
        )

        print(
            f"    trace_id  : {encounter_trace_id}"
        )

        print(
            f"    span_id   : {encounter_span_id}"
        )

        print()

        print(
            "  THRESHOLD"
        )

        print(
            f"    trace_id  : {trace_id}"
        )

        print(
            f"    span_id   : {threshold_span_id}"
        )

        print(
            f"    parent    : {encounter_span_id}"
        )

        print()

        print(
            "  status      : OPEN"
        )

        print(
            "  registry    : REGISTERED"
        )

        print(
            "  export      : WAITING FOR SPAN END"
        )

        print(
            "=============================================\n"
        )

        return threshold_span

    # ========================================================
    # ALERT RESOLUTION
    # ========================================================

    def end_alert(
        self,
        fingerprint: str,
        encounter_id: str | None,
        patient_id: str | None,
        alert_name: str | None,
        starts_at: datetime,
        ends_at: datetime,
        attributes: dict[str, Any] | None = None,
    ) -> Span | None:

        alert_span = (
            alert_span_registry.get(
                fingerprint
            )
        )

        if alert_span is None:

            print(
                "\n================ ALERT TRACE ================"
            )

            print(
                "[ALERT TRACE] ORPHANED RESOLUTION"
            )

            print(
                f"  fingerprint : {fingerprint}"
            )

            print(
                "  reason      : no active threshold "
                "span in registry"
            )

            print(
                "  action      : resolution ignored"
            )

            print(
                "=============================================\n"
            )

            return None

        threshold_attributes = (
            getattr(
                alert_span,
                "_attributes",
                {},
            )
            or {}
        )

        if encounter_id is None:
            encounter_id = (
                threshold_attributes.get(
                    "clinical.encounter.id"
                )
            )

        if patient_id is None:
            patient_id = (
                threshold_attributes.get(
                    "clinical.patient.id"
                )
            )

        if alert_name is None:
            alert_name = (
                threshold_attributes.get(
                    "clinical.alert.name",
                    "unknown",
                )
            )

        if ends_at < starts_at:
            raise ValueError(
                f"Alert ends_at cannot be earlier "
                f"than starts_at for "
                f"fingerprint={fingerprint!r}"
            )

        duration_seconds = (
            ends_at - starts_at
        ).total_seconds()

        resolution_span = (
            self.start_child_span(
                name="clinical.alert.resolution",
                parent_span=alert_span,
                start_time=ends_at,
            )
        )

        resolution_span.set_attribute(
            "clinical.alert.fingerprint",
            fingerprint,
        )

        resolution_span.set_attribute(
            "clinical.alert.name",
            alert_name,
        )

        resolution_span.set_attribute(
            "clinical.alert.status",
            "resolved",
        )

        resolution_span.set_attribute(
            "clinical.alert.phase",
            "resolution",
        )

        resolution_span.set_attribute(
            "clinical.alert.actual",
            True,
        )

        resolution_span.set_attribute(
            "clinical.alert.representation",
            "resolution",
        )

        if encounter_id:
            resolution_span.set_attribute(
                "clinical.encounter.id",
                encounter_id,
            )

        if patient_id:
            resolution_span.set_attribute(
                "clinical.patient.id",
                patient_id,
            )

        resolution_span.set_attribute(
            "clinical.alert.starts_at",
            starts_at.isoformat(),
        )

        resolution_span.set_attribute(
            "clinical.alert.ends_at",
            ends_at.isoformat(),
        )

        resolution_span.set_attribute(
            "clinical.alert.duration_seconds",
            duration_seconds,
        )

        self._apply_alert_attributes(
            resolution_span,
            attributes,
        )

        resolution_span.add_event(
            name="clinical.alert.resolved",
            timestamp=datetime_to_ns(
                ends_at
            ),
            attributes={
                "clinical.alert.fingerprint":
                    fingerprint,
                "clinical.alert.name":
                    alert_name,
                "clinical.alert.duration_seconds":
                    duration_seconds,
            },
        )

        resolution_span.end(
            end_time=datetime_to_ns(
                ends_at
            )
        )

        alert_span.set_attribute(
            "clinical.alert.status",
            "resolved",
        )

        alert_span.set_attribute(
            "clinical.alert.ends_at",
            ends_at.isoformat(),
        )

        alert_span.set_attribute(
            "clinical.alert.duration_seconds",
            duration_seconds,
        )

        alert_span.add_event(
            name="clinical.alert.threshold.ended",
            timestamp=datetime_to_ns(
                ends_at
            ),
            attributes={
                "clinical.alert.fingerprint":
                    fingerprint,
                "clinical.alert.name":
                    alert_name,
                "clinical.alert.duration_seconds":
                    duration_seconds,
            },
        )

        alert_span.end(
            end_time=datetime_to_ns(
                ends_at
            )
        )

        (
            threshold_trace_id,
            threshold_span_id,
        ) = self._alert_span_ids(
            alert_span
        )

        (
            resolution_trace_id,
            resolution_span_id,
        ) = self._alert_span_ids(
            resolution_span
        )

        print(
            "\n================ ALERT TRACE ================"
        )

        print(
            "[ALERT TRACE] RESOLVED"
        )

        print(
            f"  fingerprint : {fingerprint}"
        )

        print(
            f"  alert       : {alert_name}"
        )

        print(
            f"  encounter   : {encounter_id}"
        )

        print(
            f"  starts_at   : {starts_at.isoformat()}"
        )

        print(
            f"  ends_at     : {ends_at.isoformat()}"
        )

        print(
            f"  duration    : {duration_seconds:.3f} seconds"
        )

        print()

        print(
            "  THRESHOLD"
        )

        print(
            f"    trace_id  : {threshold_trace_id}"
        )

        print(
            f"    span_id   : {threshold_span_id}"
        )

        print()

        print(
            "  RESOLUTION"
        )

        print(
            f"    trace_id  : {resolution_trace_id}"
        )

        print(
            f"    span_id   : {resolution_span_id}"
        )

        print(
            f"    parent    : {threshold_span_id}"
        )

        print()

        print(
            "  SAME TRACE"
        )

        print(
            f"    {threshold_trace_id == resolution_trace_id}"
        )

        print()

        print(
            "  status      : CLOSED"
        )

        print(
            "  registry    : REMOVED"
        )

        print(
            "  export      : FLUSHING"
        )

        print(
            "=============================================\n"
        )

        alert_span_registry.remove(
            fingerprint
        )

        force_trace_flush()

        print(
            "[ALERT TRACE] EXPORT FLUSH COMPLETE"
        )
        print(
            f"[ALERT TRACE] trace_id={threshold_trace_id}"
        )
        print(
            f"[ALERT TRACE] threshold_span_id={threshold_span_id}"
        )
        print(
            f"[ALERT TRACE] resolution_span_id={resolution_span_id}"
        )

        return alert_span
