import time
from datetime import datetime, timezone

from app.services.trace_service import TraceService
from app.tracing.provider import configure_tracing


def main():
    configure_tracing()

    trace_service = TraceService()

    start_time = datetime.now(timezone.utc)

    print("Starting Encounter E1...")

    encounter_span = trace_service.start_encounter(
        encounter_id="E1",
        patient_id="PAT-0001",
        encounter_type="EMERGENCY",
        start_reason="NEW_ADMISSION",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
        start_time=start_time,
    )

    print("Trace ID:", format(encounter_span.get_span_context().trace_id, "032x"))
    print("Span ID:", format(encounter_span.get_span_context().span_id, "016x"))

    print("Encounter span is running...")

    time.sleep(5)

    print("Ending Encounter E1...")

    trace_service.end_encounter(
        encounter_span,
        end_time=datetime.now(timezone.utc),
        end_reason="PATIENT_DISCHARGED",
        actor_id="ADMIN-001",
        actor_role="ADMIN",
    )

    print("Encounter span ended.")

    # Give BatchSpanProcessor time to export.
    time.sleep(5)

    print("Done.")


if __name__ == "__main__":
    main()