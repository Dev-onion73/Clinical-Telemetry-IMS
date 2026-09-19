from datetime import datetime, timedelta, timezone
import time

from app.tracing.provider import configure_tracing
from app.tracing.context import serialize_span_context, context_from_ids
from app.services.trace_service import TraceService
from opentelemetry import trace


# ---------------------------------------------------------------------
# Simulated process-local registry
# ---------------------------------------------------------------------

ENCOUNTER_SPANS = {}


def register_encounter(encounter_id: str, span):
    ENCOUNTER_SPANS[encounter_id] = span


def get_encounter_span(encounter_id: str):
    return ENCOUNTER_SPANS.get(encounter_id)


def remove_encounter(encounter_id: str):
    ENCOUNTER_SPANS.pop(encounter_id, None)


# ---------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------

def main():
    configure_tracing()

    trace_service = TraceService()

    base = datetime.now(timezone.utc)

    encounter_id = "E-TEST-001"
    patient_id = "PAT-TEST-001"

    # ================================================================
    # REQUEST 1
    # Start Encounter
    # ================================================================

    print("\n=== REQUEST 1: START ENCOUNTER ===")

    encounter_span = trace_service.start_encounter(
        encounter_id=encounter_id,
        patient_id=patient_id,
        encounter_type="EMERGENCY",
        start_reason="Test admission",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
        start_time=base,
    )

    # Keep the REAL recording span alive.
    register_encounter(
        encounter_id,
        encounter_span,
    )

    persisted_context = serialize_span_context(
        encounter_span
    )

    print(
        "Encounter trace_id:",
        persisted_context["trace_id"],
    )

    print(
        "Encounter span_id:",
        persisted_context["span_id"],
    )

    print(
        "Encounter recording:",
        encounter_span.is_recording(),
    )

    # Simulate request boundary.
    del encounter_span

    # ================================================================
    # REQUEST 2
    # Create Journal under persisted Encounter context
    # ================================================================

    print("\n=== REQUEST 2: CREATE JOURNAL ===")

    parent_context = context_from_ids(
        trace_id=persisted_context["trace_id"],
        span_id=persisted_context["span_id"],
    )

    journal_span = trace_service.tracer.start_span(
        name="clinical.journal.activity",
        context=parent_context,
        start_time=int(
            (base + timedelta(seconds=5)).timestamp()
            * 1_000_000_000
        ),
    )

    journal_span.set_attribute(
        "clinical.journal.id",
        "JRN-TEST-001",
    )

    journal_span.set_attribute(
        "clinical.journal.type",
        "FIXED_ACTIVITY",
    )

    journal_span.set_attribute(
        "clinical.actor.id",
        "STAFF-001",
    )

    journal_span.set_attribute(
        "clinical.actor.role",
        "STAFF",
    )

    journal_span.end(
        int(
            (base + timedelta(seconds=8)).timestamp()
            * 1_000_000_000
        )
    )

    print(
        "Journal trace_id:",
        format(
            journal_span.get_span_context().trace_id,
            "032x",
        ),
    )

    print(
        "Journal span_id:",
        format(
            journal_span.get_span_context().span_id,
            "016x",
        ),
    )

    print(
        "Journal parent_span_id:",
        format(
            journal_span.parent.span_id,
            "016x",
        ),
    )

    print(
        "Expected parent_span_id:",
        persisted_context["span_id"],
    )

    # ================================================================
    # REQUEST 3
    # End Encounter
    # ================================================================

    print("\n=== REQUEST 3: END ENCOUNTER ===")

    encounter_span = get_encounter_span(
        encounter_id
    )

    if encounter_span is None:
        raise RuntimeError(
            "Encounter span was not found in registry"
        )

    trace_service.end_encounter(
        span=encounter_span,
        end_time=base + timedelta(seconds=15),
        end_reason="Test discharge",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
    )

    remove_encounter(encounter_id)

    print(
        "Encounter recording after end:",
        encounter_span.is_recording(),
    )

    print("Encounter removed from registry.")

    # Give BatchSpanProcessor time to export.
    print("\nWaiting for spans to export...")
    time.sleep(5)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()