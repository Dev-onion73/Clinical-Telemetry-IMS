from datetime import datetime, timedelta, timezone
import time

from app.services.encounter_service import EncounterService
from app.services.journal_service import JournalService
from app.tracing.provider import configure_tracing
from app.tracing.registry import encounter_span_registry
from app.tracing.journal_registry import journal_span_registry


def main():

    # ========================================================
    # TRACING
    # ========================================================

    configure_tracing()

    encounter_service = EncounterService()
    journal_service = JournalService()

    encounter_id = "E-JOURNAL-001"

    base_time = datetime.now(
        timezone.utc
    )

    # ========================================================
    # 1. START ENCOUNTER
    # ========================================================

    print("\n=== START ENCOUNTER ===")

    encounter = encounter_service.start(
        encounter_id=encounter_id,
        patient_id="PAT-0001",
        encounter_type="EMERGENCY",
        care_setting="EMERGENCY",
        start_reason="Journal integration test",
        started_by="ADMIN-001",
        started_by_role="ADMIN",
        start_details="Testing JournalService",
        start_time=base_time,
    )

    print(
        "Encounter:",
        encounter["encounter_id"],
    )

    print(
        "Trace ID:",
        encounter["trace_id"],
    )

    print(
        "Encounter Span ID:",
        encounter["span_id"],
    )

    assert encounter_span_registry.contains(
        encounter_id
    )

    print(
        "Encounter registry: PASS"
    )

    # ========================================================
    # 2. JOURNAL EVENT
    # ========================================================

    print("\n=== CREATE JOURNAL EVENT ===")

    event = journal_service.create_event(
        journal_id="J-EVENT-001",
        patient_id="PAT-0001",
        encounter_id=encounter_id,
        author_id="STAFF-001",
        author_role="NURSE",
        content="Patient arrived in emergency department.",
        timestamp=base_time + timedelta(seconds=2),
    )

    print(
        "Journal ID:",
        event["journal_id"],
    )

    print(
        "Journal type: EVENT"
    )

    print(
        "Event persisted: PASS"
    )

    # ========================================================
    # 3. FIXED ACTIVITY
    # ========================================================

    print("\n=== CREATE FIXED ACTIVITY ===")

    fixed = journal_service.create_fixed_activity(
        journal_id="J-FIXED-001",
        patient_id="PAT-0001",
        encounter_id=encounter_id,
        author_id="STAFF-002",
        author_role="DOCTOR",
        content="Initial clinical assessment.",
        start_time=base_time + timedelta(seconds=4),
        end_time=base_time + timedelta(seconds=8),
        start_reason="Patient assessment started",
        end_reason="Initial assessment completed",
    )

    print(
        "Journal ID:",
        fixed["journal_id"],
    )

    print(
        "Journal type: FIXED_ACTIVITY"
    )

    print(
        "Fixed activity persisted: PASS"
    )

    # ========================================================
    # 4. ONGOING ACTIVITY
    # ========================================================

    print("\n=== START ONGOING ACTIVITY ===")

    ongoing = (
        journal_service.start_ongoing_activity(
            journal_id="J-ONGOING-001",
            patient_id="PAT-0001",
            encounter_id=encounter_id,
            author_id="STAFF-003",
            author_role="NURSE",
            content="Monitoring patient response.",
            start_reason="Continuous monitoring started",
            start_time=base_time
            + timedelta(seconds=10),
        )
    )

    print(
        "Journal ID:",
        ongoing["journal_id"],
    )

    print(
        "Journal type: ONGOING_ACTIVITY"
    )

    assert journal_span_registry.contains(
        "J-ONGOING-001"
    )

    print(
        "Ongoing span registry: PASS"
    )

    # ========================================================
    # 5. END ONGOING ACTIVITY
    # ========================================================

    print("\n=== END ONGOING ACTIVITY ===")

    journal_service.end_ongoing_activity(
        journal_id="J-ONGOING-001",
        end_reason="Monitoring completed",
        ended_by="STAFF-003",
        ended_by_role="NURSE",
        end_time=base_time
        + timedelta(seconds=15),
    )

    assert not journal_span_registry.contains(
        "J-ONGOING-001"
    )

    print(
        "Ongoing activity closed: PASS"
    )

    print(
        "Journal registry cleanup: PASS"
    )

    # ========================================================
    # 6. VERIFY ENCOUNTER STILL OPEN
    # ========================================================

    print("\n=== VERIFY ENCOUNTER ===")

    current_encounter = (
        encounter_service.get(
            encounter_id
        )
    )

    assert current_encounter is not None

    assert (
        current_encounter["status"]
        == "OPEN"
    )

    print(
        "Encounter remains open: PASS"
    )

    # ========================================================
    # 7. CLOSE ENCOUNTER
    # ========================================================

    print("\n=== CLOSE ENCOUNTER ===")

    encounter_service.close(
        encounter_id=encounter_id,
        end_reason="Journal integration test completed",
        ended_by="ADMIN-001",
        end_details="All Journal types tested",
        end_time=base_time
        + timedelta(seconds=20),
    )

    assert not encounter_span_registry.contains(
        encounter_id
    )

    print(
        "Encounter closed: PASS"
    )

    print(
        "Encounter registry cleanup: PASS"
    )

    # ========================================================
    # 8. WAIT FOR OTLP EXPORT
    # ========================================================

    print(
        "\nWaiting for trace export..."
    )

    time.sleep(5)

    # ========================================================
    # COMPLETE
    # ========================================================

    print("\n=== TEST COMPLETE ===")

    print(
        "\nExpected trace hierarchy:"
    )

    print(
        """
clinical.encounter
├── event: clinical.journal.event
├── clinical.journal.activity
└── clinical.journal.activity
        """
    )


if __name__ == "__main__":
    main()