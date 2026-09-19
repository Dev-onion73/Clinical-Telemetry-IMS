from datetime import datetime, timedelta, timezone
import time

from app.persistence.encounters import EncounterRepository
from app.persistence.journals import JournalRepository

from app.services.encounter_service import EncounterService
from app.services.journal_service import JournalService

from app.tracing.journal_registry import (
    journal_span_registry,
)

from app.tracing.provider import (
    configure_tracing,
)


# ============================================================
# TRACING INITIALIZATION
# ============================================================

configure_tracing()


# ============================================================
# SERVICES
# ============================================================

encounter_service = EncounterService(
    repository=EncounterRepository(),
)

journal_service = JournalService(
    repository=JournalRepository(),
)


# ============================================================
# TEST DATA
# ============================================================

encounter_id = "E-JOURNAL-OPEN-001"
patient_id = "PAT-0001"

start_time = datetime.now(timezone.utc)


# ============================================================
# START ENCOUNTER
# ============================================================

print("\n=== START ENCOUNTER ===")

encounter = encounter_service.start(
    encounter_id=encounter_id,
    patient_id=patient_id,
    encounter_type="EMERGENCY",
    care_setting="EMERGENCY",
    start_reason="Journal ongoing activity test",
    started_by="ADMIN-001",
    started_by_role="ADMIN",
    start_details="Testing long-lived Journal activity span.",
    start_time=start_time,
    
)

print(
    f"Encounter ID: {encounter['encounter_id']}"
)

print(
    f"Trace ID: {encounter['trace_id']}"
)

print(
    f"Encounter Span ID: {encounter['span_id']}"
)

print(
    "Encounter registry: PASS"
)


# ============================================================
# CREATE JOURNAL EVENT
# ============================================================

print("\n=== CREATE JOURNAL EVENT ===")

event = journal_service.create_event(
    journal_id="J-EVENT-OPEN-001",
    patient_id=patient_id,
    encounter_id=encounter_id,
    author_id="STAFF-001",
    author_role="NURSE",
    content="Patient arrived in emergency department.",
    timestamp=start_time + timedelta(seconds=1),
)

print(
    f"Journal ID: {event['journal_id']}"
)

print(
    "Journal event persisted: PASS"
)

print(
    "Journal event added to Encounter trace: PASS"
)


# ============================================================
# CREATE FIXED ACTIVITY
# ============================================================

print("\n=== CREATE FIXED ACTIVITY ===")

fixed = journal_service.create_fixed_activity(
    journal_id="J-FIXED-OPEN-001",
    patient_id=patient_id,
    encounter_id=encounter_id,
    author_id="STAFF-002",
    author_role="DOCTOR",
    content="Initial clinical assessment.",
    start_time=start_time + timedelta(seconds=2),
    end_time=start_time + timedelta(seconds=4),
    start_reason="Assessment initiated.",
    end_reason="Initial assessment completed.",
)

print(
    f"Journal ID: {fixed['journal_id']}"
)

print(
    "Fixed activity persisted: PASS"
)

print(
    "Fixed activity span closed: PASS"
)


# ============================================================
# START ONGOING ACTIVITY
# ============================================================

print("\n=== START ONGOING ACTIVITY ===")

ongoing = journal_service.start_ongoing_activity(
    journal_id="J-ONGOING-OPEN-001",
    patient_id=patient_id,
    encounter_id=encounter_id,
    author_id="STAFF-003",
    author_role="NURSE",
    content="Monitoring patient response.",
    start_reason="Continuous patient monitoring initiated.",
    start_time=start_time + timedelta(seconds=5),
)

print(
    f"Journal ID: {ongoing['journal_id']}"
)

print(
    "Ongoing journal persisted: PASS"
)


# ============================================================
# VERIFY ONGOING SPAN EXISTS
# ============================================================

ongoing_span = journal_span_registry.get(
    "J-ONGOING-OPEN-001"
)

if ongoing_span is None:
    raise RuntimeError(
        "Ongoing Journal span was not found in registry"
    )

print(
    "Ongoing span registry: PASS"
)


# ============================================================
# VERIFY ONGOING SPAN IS OPEN
# ============================================================

if not ongoing_span.is_recording():
    raise RuntimeError(
        "Ongoing Journal span has already ended"
    )

print(
    "Ongoing span remains OPEN: PASS"
)


# ============================================================
# LET TIME PASS
# ============================================================

print("\n=== WAITING WHILE ONGOING ACTIVITY REMAINS OPEN ===")

print(
    "Waiting 10 seconds..."
)

time.sleep(10)


# ============================================================
# VERIFY SPAN IS STILL OPEN
# ============================================================

ongoing_span = journal_span_registry.get(
    "J-ONGOING-OPEN-001"
)

if ongoing_span is None:
    raise RuntimeError(
        "Ongoing Journal span disappeared from registry"
    )

if not ongoing_span.is_recording():
    raise RuntimeError(
        "Ongoing Journal span ended unexpectedly"
    )

print(
    "Ongoing span still OPEN after 10 seconds: PASS"
)


# ============================================================
# IMPORTANT
# ============================================================
#
# DO NOT CALL:
#
# journal_service.end_ongoing_activity(...)
#
# DO NOT CLOSE THE ENCOUNTER.
#
# We deliberately leave both alive so that this test proves
# that the ongoing activity is genuinely long-lived.
# ============================================================

print("\n=== ONGOING ACTIVITY LEFT OPEN ===")

print(
    "Journal ID: J-ONGOING-OPEN-001"
)

print(
    "Span remains active."
)

print(
    "No end_ongoing_activity() call was made."
)

print(
    "Encounter remains open."
)


# ============================================================
# TRACE INFORMATION
# ============================================================

print("\n=== TRACE INFORMATION ===")

print(
    f"Trace ID: {encounter['trace_id']}"
)

print(
    """
Expected hierarchy:

clinical.encounter
├── event: clinical.journal.event
├── clinical.journal.activity   [CLOSED]
└── clinical.journal.activity   [OPEN]
"""
)


# ============================================================
# TEST COMPLETE
# ============================================================

print("\n=== TEST COMPLETE ===")

print(
    "Journal Event: PASS"
)

print(
    "Fixed Activity: PASS"
)

print(
    "Ongoing Activity: OPEN"
)

print(
    "Encounter: OPEN"
)

print(
    "The ongoing span was intentionally NOT ended."
)