from datetime import datetime, timedelta, timezone

from app.services.trace_service import TraceService
from app.tracing.provider import configure_tracing


def main():
    configure_tracing()

    trace_service = TraceService()

    base = datetime.now(timezone.utc)

    # ==================================================
    # ENCOUNTER — 20 seconds
    # ==================================================

    encounter = trace_service.start_encounter(
        encounter_id="E1",
        patient_id="PAT-0001",
        encounter_type="EMERGENCY",
        start_reason="NEW_ADMISSION",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
        start_time=base,
    )

    print("Encounter")
    print(
        "  Trace ID:",
        format(
            encounter.get_span_context().trace_id,
            "032x",
        ),
    )
    print(
        "  Span ID:",
        format(
            encounter.get_span_context().span_id,
            "016x",
        ),
    )

    # ==================================================
    # JOURNAL — starts at +4s, lasts 3s
    # ==================================================

    journal_start = base + timedelta(seconds=4)
    journal_end = base + timedelta(seconds=7)

    journal = trace_service.start_child_span(
        name="clinical.journal.activity",
        parent_span=encounter,
        start_time=journal_start,
    )

    journal.set_attribute(
        "clinical.journal.id",
        "JRN-001",
    )

    journal.set_attribute(
        "clinical.journal.entry_type",
        "FIXED_ACTIVITY",
    )

    journal.set_attribute(
        "clinical.actor.id",
        "STAFF-001",
    )

    journal.set_attribute(
        "clinical.actor.role",
        "STAFF",
    )

    print("\nJournal Activity")
    print(
        "  Trace ID:",
        format(
            journal.get_span_context().trace_id,
            "032x",
        ),
    )

    print(
        "  Span ID:",
        format(
            journal.get_span_context().span_id,
            "016x",
        ),
    )

    print(
        "  Parent Span ID:",
        format(
            journal.parent.span_id,
            "016x",
        ),
    )

    journal.end(
        end_time=int(
            journal_end.timestamp()
            * 1_000_000_000
        )
    )

    # ==================================================
    # SECOND JOURNAL — starts at +11s, lasts 2s
    # ==================================================

    journal2_start = base + timedelta(seconds=11)
    journal2_end = base + timedelta(seconds=13)

    journal2 = trace_service.start_child_span(
        name="clinical.journal.activity",
        parent_span=encounter,
        start_time=journal2_start,
    )

    journal2.set_attribute(
        "clinical.journal.id",
        "JRN-002",
    )

    journal2.set_attribute(
        "clinical.journal.entry_type",
        "ONGOING_ACTIVITY",
    )

    journal2.set_attribute(
        "clinical.actor.id",
        "STAFF-002",
    )

    journal2.set_attribute(
        "clinical.actor.role",
        "STAFF",
    )

    journal2.end(
        end_time=int(
            journal2_end.timestamp()
            * 1_000_000_000
        )
    )

    # ==================================================
    # END ENCOUNTER — +20s
    # ==================================================

    encounter_end = base + timedelta(seconds=20)

    trace_service.end_encounter(
        encounter,
        end_time=encounter_end,
        end_reason="PATIENT_DISCHARGED",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
    )

    print("\nTrace complete.")

    # Allow BatchSpanProcessor to export.
    import time
    time.sleep(5)


if __name__ == "__main__":
    main()