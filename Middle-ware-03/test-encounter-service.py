from datetime import datetime, timedelta, timezone
import time

from app.services.encounter_service import EncounterService
from app.tracing.provider import configure_tracing
from app.tracing.registry import encounter_span_registry


def main():

    configure_tracing()

    service = EncounterService()

    encounter_id = "E-SVC-001"

    base = datetime.now(timezone.utc)

    print("\n=== START ENCOUNTER ===")

    encounter = service.start(
        encounter_id=encounter_id,
        patient_id="PAT-0001",
        encounter_type="EMERGENCY",
        care_setting="EMERGENCY",
        start_reason="Clinical middleware integration test",
        started_by="ADMIN-001",
        started_by_role="ADMIN",
        start_details="Testing EncounterService tracing integration",
        start_time=base,
    )

    print("Encounter ID:")
    print(encounter["encounter_id"])

    print("Trace ID:")
    print(encounter["trace_id"])

    print("Span ID:")
    print(encounter["span_id"])

    print(
        "Registry contains encounter:",
        encounter_span_registry.contains(
            encounter_id
        ),
    )

    print("\n=== VERIFY START ===")

    assert encounter["status"] == "OPEN"

    assert encounter["trace_id"] is not None
    assert len(encounter["trace_id"]) == 32

    assert encounter["span_id"] is not None
    assert len(encounter["span_id"]) == 16

    assert encounter_span_registry.contains(
        encounter_id
    )

    print("Encounter persistence: PASS")
    print("Trace identity persistence: PASS")
    print("Registry registration: PASS")

    print("\n=== DATABASE LOOKUP ===")

    persisted = service.get(
        encounter_id
    )

    print(
        "Persisted trace_id:",
        persisted["trace_id"],
    )

    print(
        "Persisted span_id:",
        persisted["span_id"],
    )

    assert (
        persisted["trace_id"]
        == encounter["trace_id"]
    )

    assert (
        persisted["span_id"]
        == encounter["span_id"]
    )

    print("Trace identity round-trip: PASS")

    print("\n=== CLOSE ENCOUNTER ===")

    service.close(
        encounter_id=encounter_id,
        end_reason="Integration test completed",
        ended_by="ADMIN-001",
        end_details="Closing test encounter",
        end_time=base + timedelta(seconds=10),
    )

    print("\n=== VERIFY CLOSE ===")

    closed = service.get(
        encounter_id
    )

    print(
        "Status:",
        closed["status"],
    )

    print(
        "End reason:",
        closed["end_reason"],
    )

    print(
        "Ended by:",
        closed["ended_by"],
    )

    print(
        "Registry contains encounter:",
        encounter_span_registry.contains(
            encounter_id
        ),
    )

    assert closed["status"] == "CLOSED"

    assert (
        closed["end_reason"]
        == "Integration test completed"
    )

    assert (
        closed["ended_by"]
        == "ADMIN-001"
    )

    assert not encounter_span_registry.contains(
        encounter_id
    )

    print("Encounter closure: PASS")
    print("Registry cleanup: PASS")

    print("\nWaiting for trace export...")
    time.sleep(5)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()