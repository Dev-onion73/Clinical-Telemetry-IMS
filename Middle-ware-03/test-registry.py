from datetime import datetime, timedelta, timezone
import time

from app.services.trace_service import TraceService
from app.tracing.context import serialize_span_context
from app.tracing.provider import configure_tracing
from app.tracing.registry import encounter_span_registry


def main():
    configure_tracing()

    trace_service = TraceService()

    base = datetime.now(timezone.utc)

    encounter_id = "E-REG-001"

    # ================================================================
    # 1. START ENCOUNTER
    # ================================================================

    print("\n=== START ENCOUNTER ===")

    encounter_span = trace_service.start_encounter(
        encounter_id=encounter_id,
        patient_id="PAT-REG-001",
        encounter_type="EMERGENCY",
        start_reason="Registry integration test",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
        start_time=base,
    )

    context_data = serialize_span_context(
        encounter_span
    )

    print("Encounter trace_id:")
    print(context_data["trace_id"])

    print("Encounter span_id:")
    print(context_data["span_id"])

    print(
        "Registry contains encounter:",
        encounter_span_registry.contains(encounter_id),
    )

    print(
        "Span recording:",
        encounter_span.is_recording(),
    )

    # ================================================================
    # 2. RETRIEVE ENCOUNTER FROM REGISTRY
    # ================================================================

    print("\n=== REGISTRY LOOKUP ===")

    registered_span = encounter_span_registry.get(
        encounter_id
    )

    if registered_span is None:
        raise RuntimeError(
            "Encounter was not found in registry"
        )

    print(
        "Same Span object:",
        registered_span is encounter_span,
    )

    print(
        "Registry Span ID:",
        format(
            registered_span.get_span_context().span_id,
            "016x",
        ),
    )

    # ================================================================
    # 3. CREATE JOURNAL CHILD
    # ================================================================

    print("\n=== CREATE JOURNAL CHILD ===")

    journal_span = trace_service.start_child_span(
        name="clinical.journal.activity",
        parent_span=registered_span,
        start_time=base + timedelta(seconds=5),
    )

    journal_span.set_attribute(
        "clinical.journal.id",
        "JRN-REG-001",
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
        end_time=int(
            (
                base + timedelta(seconds=8)
            ).timestamp()
            * 1_000_000_000
        )
    )

    journal_trace_id = format(
        journal_span.get_span_context().trace_id,
        "032x",
    )

    journal_parent_id = format(
        journal_span.parent.span_id,
        "016x",
    )

    print("Journal trace_id:")
    print(journal_trace_id)

    print("Journal parent_span_id:")
    print(journal_parent_id)

    print("Expected trace_id:")
    print(context_data["trace_id"])

    print("Expected parent_span_id:")
    print(context_data["span_id"])

    # ================================================================
    # 4. VERIFY PARENT RELATIONSHIP
    # ================================================================

    print("\n=== VERIFY RELATIONSHIP ===")

    if journal_trace_id != context_data["trace_id"]:
        raise AssertionError(
            "Journal does not belong to Encounter trace"
        )

    if journal_parent_id != context_data["span_id"]:
        raise AssertionError(
            "Journal is not a child of Encounter"
        )

    print("Trace ID relationship: PASS")
    print("Parent-child relationship: PASS")

    # ================================================================
    # 5. END ENCOUNTER
    # ================================================================

    print("\n=== END ENCOUNTER ===")

    trace_service.end_encounter(
        encounter_id=encounter_id,
        end_time=base + timedelta(seconds=15),
        end_reason="Registry integration test complete",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
    )

    print(
        "Registry contains encounter after end:",
        encounter_span_registry.contains(encounter_id),
    )

    if encounter_span_registry.contains(encounter_id):
        raise AssertionError(
            "Encounter span was not removed from registry"
        )

    print("Registry cleanup: PASS")

    # ================================================================
    # 6. EXPORT
    # ================================================================

    print("\nWaiting for spans to export...")
    time.sleep(5)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()