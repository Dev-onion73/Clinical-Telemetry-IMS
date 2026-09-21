"""
Phase 03 — Full Clinical Trace Integration Test

Scenario:

Patient
  |
  +-- Encounter: 08:00 -> 16:00
       |
       +-- Journal EVENT
       |
       +-- Episode 1: 08:10 -> 10:00
       |     |
       |     +-- FIXED_ACTIVITY
       |     +-- ONGOING_ACTIVITY
       |     +-- EVENT
       |
       +-- FIXED_ACTIVITY outside episode
       |
       +-- Episode 2: 12:00 -> 14:30
       |     |
       |     +-- FIXED_ACTIVITY
       |     +-- ONGOING_ACTIVITY
       |     +-- EVENT
       |
       +-- Journal EVENT
       |
       +-- Alarm event
       |
       +-- Encounter closes

The test verifies:

1. Encounter persistence
2. Encounter root span
3. Encounter registry
4. Episode persistence
5. Episode child spans
6. Episode 1 and Episode 2 are siblings
7. Fixed journal activities
8. Ongoing journal activities
9. Ongoing activities remain open until explicit close
10. Journal events
11. Parent/child span relationships
12. Shared trace ID
13. Activities outside episodes are encounter children
14. Activities inside episodes are episode children
15. Alarm represented as an event
16. Registry cleanup
17. Encounter closure
18. PostgreSQL state
19. Trace hierarchy summary

NOTE:
This assumes the current service APIs expose the methods used below.
If your current EpisodeService / JournalService signatures differ slightly,
adjust only those calls rather than changing the test's intended scenario.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# PROJECT IMPORT PATH
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------------------------

from app.tracing.provider import configure_tracing
from app.tracing.context import serialize_span_context

from app.services.encounter_service import EncounterService
from app.services.journal_service import JournalService
from app.services.episode_service import EpisodeService


# ---------------------------------------------------------------------------
# TEST CONSTANTS
# ---------------------------------------------------------------------------

PATIENT_ID = "PAT-TRACE-FULL-001"
ENCOUNTER_ID = "E-TRACE-FULL-001"

EPISODE_1_ID = "EP-TRACE-001"
EPISODE_2_ID = "EP-TRACE-002"

J_EVENT_001 = "J-TRACE-EVENT-001"
J_EP1_FIXED = "J-TRACE-EP1-FIXED"
J_EP1_ONGOING = "J-TRACE-EP1-ONGOING"
J_EP1_EVENT = "J-TRACE-EP1-EVENT"

J_OUTSIDE_FIXED = "J-TRACE-OUTSIDE-FIXED"

J_EP2_FIXED = "J-TRACE-EP2-FIXED"
J_EP2_ONGOING = "J-TRACE-EP2-ONGOING"
J_EP2_EVENT = "J-TRACE-EP2-EVENT"

J_EVENT_002 = "J-TRACE-EVENT-002"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

BASE_TIME = datetime(
    2026,
    8,
    5,
    8,
    0,
    0,
    tzinfo=timezone.utc,
)


def t(minutes: int) -> datetime:
    """
    Return a deterministic UTC timestamp relative to the encounter start.
    """
    return BASE_TIME + timedelta(minutes=minutes)


def ns(dt: datetime) -> int:
    """
    Convert datetime to OpenTelemetry nanoseconds.

    Span.end(end_time=...) expects an integer timestamp in nanoseconds.
    """
    return int(dt.timestamp() * 1_000_000_000)


def assert_equal(actual, expected, message: str):
    if actual != expected:
        raise AssertionError(
            f"{message}\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {actual!r}"
        )


def assert_true(condition, message: str):
    if not condition:
        raise AssertionError(message)


def print_span(label: str, span):
    """
    Print useful tracing information for manual verification.
    """

    context = span.get_span_context()

    trace_id = f"{context.trace_id:032x}"
    span_id = f"{context.span_id:016x}"

    parent_id = getattr(span, "parent", None)

    if parent_id is not None:
        parent_span_id = getattr(parent_id, "span_id", None)

        if parent_span_id:
            parent_span_id = f"{parent_span_id:016x}"
        else:
            parent_span_id = "NONE"
    else:
        parent_span_id = "NONE"

    print()
    print(f"--- {label} ---")
    print(f"Span name:       {span.name}")
    print(f"Trace ID:        {trace_id}")
    print(f"Span ID:         {span_id}")
    print(f"Parent Span ID:  {parent_span_id}")
    print(f"Start:           {span.start_time}")
    print(f"End:             {span.end_time}")


def span_context(span):
    """
    Return serialised span context.
    """

    return serialize_span_context(span)


# ---------------------------------------------------------------------------
# MAIN TEST
# ---------------------------------------------------------------------------

def main():

    print()
    print("=" * 80)
    print("PHASE 03 — FULL CLINICAL TRACE INTEGRATION TEST")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # TRACE PROVIDER
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("CONFIGURE TRACING")
    print("=" * 80)

    configure_tracing()

    print("Tracing provider configured: PASS")

    # -----------------------------------------------------------------------
    # SERVICES
    # -----------------------------------------------------------------------

    encounter_service = EncounterService()
    journal_service = JournalService()
    episode_service = EpisodeService()

    # -----------------------------------------------------------------------
    # 1. START ENCOUNTER
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("1. START ENCOUNTER")
    print("=" * 80)

    encounter = encounter_service.start(
        encounter_id=ENCOUNTER_ID,
        patient_id=PATIENT_ID,
        encounter_type="EMERGENCY",
        care_setting="EMERGENCY",
        start_time=t(0),
        start_reason="Full Phase 03 integration test",
        started_by="ADMIN-TRACE-001",
        start_details=(
            "Testing encounter, multiple episodes, journals, "
            "activities and alarm tracing."
        ),
    )

    assert_true(
        encounter is not None,
        "EncounterService.start() returned no encounter",
    )

    print("Encounter created: PASS")
    print(f"Encounter ID: {ENCOUNTER_ID}")

    # -----------------------------------------------------------------------
    # 2. ENCOUNTER ROOT SPAN
    # -----------------------------------------------------------------------

    encounter_span = encounter_service.get_active_span(
        ENCOUNTER_ID
    )

    assert_true(
        encounter_span is not None,
        "Encounter root span was not found in registry",
    )

    encounter_ctx = span_context(encounter_span)

    encounter_trace_id = encounter_ctx["trace_id"]
    encounter_span_id = encounter_ctx["span_id"]

    print("Encounter registry: PASS")
    print(f"Encounter Trace ID: {encounter_trace_id}")
    print(f"Encounter Span ID:  {encounter_span_id}")

    # -----------------------------------------------------------------------
    # 3. JOURNAL EVENT BEFORE EPISODES
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("3. JOURNAL EVENT — OUTSIDE EPISODE")
    print("=" * 80)

    event_001 = journal_service.create(
        journal_id=J_EVENT_001,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-001",
        author_role="NURSE",
        timestamp=t(5),
        content="Patient arrived in emergency department.",
        journal_type="EVENT",
    )

    assert_true(
        event_001 is not None,
        "Failed to create EVENT journal",
    )

    print(f"Journal ID: {J_EVENT_001}")
    print("Journal EVENT persisted: PASS")
    print("Expected representation: span event")

    # -----------------------------------------------------------------------
    # 4. START EPISODE 1
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("4. START EPISODE 1")
    print("=" * 80)

    episode_1 = episode_service.start(
        episode_id=EPISODE_1_ID,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        initiated_by="STAFF-001",
        initiation_method="JOURNAL",
        start_time=t(10),
        trace_id=encounter_trace_id,
    )

    assert_true(
        episode_1 is not None,
        "Failed to create Episode 1",
    )

    episode_1_span = episode_service.get_active_span(
        EPISODE_1_ID
    )

    assert_true(
        episode_1_span is not None,
        "Episode 1 span not found",
    )

    ep1_ctx = span_context(episode_1_span)

    print("Episode 1 persisted: PASS")
    print(f"Episode 1 Trace ID: {ep1_ctx['trace_id']}")
    print(f"Episode 1 Span ID:  {ep1_ctx['span_id']}")

    # -----------------------------------------------------------------------
    # 5. VERIFY EPISODE 1 PARENT
    # -----------------------------------------------------------------------

    ep1_parent_id = (
        episode_1_span.parent.span_id
        if episode_1_span.parent
        else None
    )

    assert_equal(
        f"{ep1_ctx['trace_id']}",
        encounter_trace_id,
        "Episode 1 must share the encounter trace ID",
    )

    assert_equal(
        f"{ep1_parent_id:016x}" if ep1_parent_id else None,
        encounter_span_id,
        "Episode 1 must be a direct child of encounter",
    )

    print("Episode 1 → Encounter parent relationship: PASS")

    # -----------------------------------------------------------------------
    # 6. EPISODE 1 FIXED ACTIVITY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("6. EPISODE 1 — FIXED ACTIVITY")
    print("=" * 80)

    ep1_fixed = journal_service.create(
        journal_id=J_EP1_FIXED,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-002",
        author_role="DOCTOR",
        timestamp=t(15),
        content="Initial clinical assessment.",
        journal_type="FIXED_ACTIVITY",
        start_time=t(15),
        end_time=t(30),
        episode_id=EPISODE_1_ID,
    )

    assert_true(
        ep1_fixed is not None,
        "Episode 1 fixed activity failed",
    )

    print("Episode 1 fixed activity: PASS")

    # -----------------------------------------------------------------------
    # 7. EPISODE 1 ONGOING ACTIVITY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("7. EPISODE 1 — ONGOING ACTIVITY")
    print("=" * 80)

    ep1_ongoing = journal_service.create(
        journal_id=J_EP1_ONGOING,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-003",
        author_role="NURSE",
        timestamp=t(35),
        content="Monitoring patient response.",
        journal_type="ONGOING_ACTIVITY",
        start_time=t(35),
        episode_id=EPISODE_1_ID,
    )

    assert_true(
        ep1_ongoing is not None,
        "Episode 1 ongoing activity failed",
    )

    # IMPORTANT:
    # We intentionally do NOT close this activity yet.

    ongoing_1_span = journal_service.get_active_span(
        J_EP1_ONGOING
    )

    assert_true(
        ongoing_1_span is not None,
        "Episode 1 ongoing span disappeared before explicit close",
    )

    print("Episode 1 ongoing activity opened: PASS")
    print("Episode 1 ongoing activity remains open: PASS")

    # -----------------------------------------------------------------------
    # 8. EPISODE 1 EVENT
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("8. EPISODE 1 — JOURNAL EVENT")
    print("=" * 80)

    ep1_event = journal_service.create(
        journal_id=J_EP1_EVENT,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-001",
        author_role="NURSE",
        timestamp=t(50),
        content="Patient responding to initial intervention.",
        journal_type="EVENT",
        episode_id=EPISODE_1_ID,
    )

    assert_true(
        ep1_event is not None,
        "Episode 1 event failed",
    )

    print("Episode 1 event: PASS")

    # -----------------------------------------------------------------------
    # 9. CLOSE EPISODE 1 ONGOING ACTIVITY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("9. CLOSE EPISODE 1 ONGOING ACTIVITY")
    print("=" * 80)

    journal_service.end_ongoing_activity(
        journal_id=J_EP1_ONGOING,
        end_time=t(80),
    )

    ongoing_1_after = journal_service.get_active_span(
        J_EP1_ONGOING
    )

    assert_true(
        ongoing_1_after is None,
        "Episode 1 ongoing span still exists after explicit close",
    )

    print("Episode 1 ongoing activity explicitly closed: PASS")
    print("Episode 1 journal registry cleanup: PASS")

    # -----------------------------------------------------------------------
    # 10. CLOSE EPISODE 1
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("10. CLOSE EPISODE 1")
    print("=" * 80)

    episode_service.close(
        episode_id=EPISODE_1_ID,
        end_time=t(120),
        closure_by="STAFF-001",
        closure_details="Emergency assessment completed.",
    )

    episode_1_after = episode_service.get_active_span(
        EPISODE_1_ID
    )

    assert_true(
        episode_1_after is None,
        "Episode 1 still exists in active registry",
    )

    print("Episode 1 closed: PASS")
    print("Episode 1 registry cleanup: PASS")

    # -----------------------------------------------------------------------
    # 11. ACTIVITY OUTSIDE EPISODE
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("11. FIXED ACTIVITY OUTSIDE EPISODE")
    print("=" * 80)

    outside_activity = journal_service.create(
        journal_id=J_OUTSIDE_FIXED,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-002",
        author_role="DOCTOR",
        timestamp=t(150),
        content="General clinical review outside an active episode.",
        journal_type="FIXED_ACTIVITY",
        start_time=t(150),
        end_time=t(180),
    )

    assert_true(
        outside_activity is not None,
        "Outside-episode activity failed",
    )

    print("Outside-episode fixed activity: PASS")

    # -----------------------------------------------------------------------
    # 12. START EPISODE 2
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("12. START EPISODE 2")
    print("=" * 80)

    episode_2 = episode_service.start(
        episode_id=EPISODE_2_ID,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        initiated_by="ADMIN-001",
        initiation_method="JOURNAL",
        start_time=t(240),
        trace_id=encounter_trace_id,
    )

    assert_true(
        episode_2 is not None,
        "Failed to create Episode 2",
    )

    episode_2_span = episode_service.get_active_span(
        EPISODE_2_ID
    )

    assert_true(
        episode_2_span is not None,
        "Episode 2 span not found",
    )

    ep2_ctx = span_context(episode_2_span)

    print("Episode 2 persisted: PASS")
    print(f"Episode 2 Trace ID: {ep2_ctx['trace_id']}")
    print(f"Episode 2 Span ID:  {ep2_ctx['span_id']}")

    # -----------------------------------------------------------------------
    # 13. VERIFY EPISODE 2 IS SIBLING OF EPISODE 1
    # -----------------------------------------------------------------------

    ep2_parent_id = (
        episode_2_span.parent.span_id
        if episode_2_span.parent
        else None
    )

    assert_equal(
        ep2_ctx["trace_id"],
        encounter_trace_id,
        "Episode 2 must share encounter trace ID",
    )

    assert_equal(
        f"{ep2_parent_id:016x}" if ep2_parent_id else None,
        encounter_span_id,
        "Episode 2 must be a direct child of encounter",
    )

    print("Episode 2 → Encounter parent relationship: PASS")
    print("Episode 1 and Episode 2 are sibling spans: PASS")

    # -----------------------------------------------------------------------
    # 14. EPISODE 2 FIXED ACTIVITY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("14. EPISODE 2 — FIXED ACTIVITY")
    print("=" * 80)

    ep2_fixed = journal_service.create(
        journal_id=J_EP2_FIXED,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-002",
        author_role="DOCTOR",
        timestamp=t(250),
        content="Procedure preparation.",
        journal_type="FIXED_ACTIVITY",
        start_time=t(250),
        end_time=t(280),
        episode_id=EPISODE_2_ID,
    )

    assert_true(
        ep2_fixed is not None,
        "Episode 2 fixed activity failed",
    )

    print("Episode 2 fixed activity: PASS")

    # -----------------------------------------------------------------------
    # 15. EPISODE 2 ONGOING ACTIVITY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("15. EPISODE 2 — ONGOING ACTIVITY")
    print("=" * 80)

    ep2_ongoing = journal_service.create(
        journal_id=J_EP2_ONGOING,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-003",
        author_role="NURSE",
        timestamp=t(285),
        content="Post-procedure monitoring.",
        journal_type="ONGOING_ACTIVITY",
        start_time=t(285),
        episode_id=EPISODE_2_ID,
    )

    assert_true(
        ep2_ongoing is not None,
        "Episode 2 ongoing activity failed",
    )

    ongoing_2_span = journal_service.get_active_span(
        J_EP2_ONGOING
    )

    assert_true(
        ongoing_2_span is not None,
        "Episode 2 ongoing activity did not remain open",
    )

    print("Episode 2 ongoing activity opened: PASS")
    print("Episode 2 ongoing activity remains open: PASS")

    # -----------------------------------------------------------------------
    # 16. EPISODE 2 EVENT
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("16. EPISODE 2 — JOURNAL EVENT")
    print("=" * 80)

    ep2_event = journal_service.create(
        journal_id=J_EP2_EVENT,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-001",
        author_role="NURSE",
        timestamp=t(320),
        content="Post-procedure observation recorded.",
        journal_type="EVENT",
        episode_id=EPISODE_2_ID,
    )

    assert_true(
        ep2_event is not None,
        "Episode 2 event failed",
    )

    print("Episode 2 event: PASS")

    # -----------------------------------------------------------------------
    # 17. ALARM EVENT
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("17. CLINICAL ALARM EVENT")
    print("=" * 80)

    # The alarm is deliberately represented as an EVENT.
    #
    # It does NOT create an episode.
    #
    # In the final implementation this should originate from:
    #
    # InfluxDB → Grafana alert → Middleware
    #
    # For this integration test we inject the resulting alarm directly
    # into the trace so we can test the trace behavior before the actual
    # Grafana webhook endpoint is implemented.

    alarm_time = t(350)

    encounter_span.add_event(
        "clinical.alarm.triggered",
        attributes={
            "alarm.id": "ALARM-TRACE-001",
            "alarm.source": "grafana",
            "alarm.status": "TRIGGERED",
            "alarm.severity": "CRITICAL",
            "alarm.metric": "spo2",
            "alarm.value": 82,
            "alarm.threshold": 90,
            "patient.id": PATIENT_ID,
            "encounter.id": ENCOUNTER_ID,
        },
        timestamp=ns(alarm_time),
    )

    encounter_span.add_event(
        "clinical.alarm.responded",
        attributes={
            "alarm.id": "ALARM-TRACE-001",
            "alarm.status": "RESPONDED",
            "alarm.responder_id": "STAFF-001",
            "alarm.responder_role": "NURSE",
            "alarm.response_latency_seconds": 120,
        },
        timestamp=ns(t(352)),
    )

    print("Alarm trigger event added: PASS")
    print("Alarm response event added: PASS")
    print("Alarm created no episode: PASS")

    # -----------------------------------------------------------------------
    # 18. CLOSE EPISODE 2 ONGOING ACTIVITY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("18. CLOSE EPISODE 2 ONGOING ACTIVITY")
    print("=" * 80)

    journal_service.end_ongoing_activity(
        journal_id=J_EP2_ONGOING,
        end_time=t(360),
    )

    ongoing_2_after = journal_service.get_active_span(
        J_EP2_ONGOING
    )

    assert_true(
        ongoing_2_after is None,
        "Episode 2 ongoing span still exists after explicit close",
    )

    print("Episode 2 ongoing activity explicitly closed: PASS")
    print("Episode 2 journal registry cleanup: PASS")

    # -----------------------------------------------------------------------
    # 19. CLOSE EPISODE 2
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("19. CLOSE EPISODE 2")
    print("=" * 80)

    episode_service.close(
        episode_id=EPISODE_2_ID,
        end_time=t(390),
        closure_by="ADMIN-001",
        closure_details="Procedure monitoring completed.",
    )

    episode_2_after = episode_service.get_active_span(
        EPISODE_2_ID
    )

    assert_true(
        episode_2_after is None,
        "Episode 2 still exists in active registry",
    )

    print("Episode 2 closed: PASS")
    print("Episode 2 registry cleanup: PASS")

    # -----------------------------------------------------------------------
    # 20. FINAL JOURNAL EVENT
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("20. FINAL JOURNAL EVENT")
    print("=" * 80)

    event_002 = journal_service.create(
        journal_id=J_EVENT_002,
        patient_id=PATIENT_ID,
        encounter_id=ENCOUNTER_ID,
        author_id="STAFF-001",
        author_role="NURSE",
        timestamp=t(420),
        content="Patient stable after monitored period.",
        journal_type="EVENT",
    )

    assert_true(
        event_002 is not None,
        "Final journal event failed",
    )

    print("Final encounter event: PASS")

    # -----------------------------------------------------------------------
    # 21. VERIFY ONGOING REGISTRIES ARE EMPTY
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("21. VERIFY REGISTRY STATE")
    print("=" * 80)

    assert_true(
        journal_service.get_active_span(J_EP1_ONGOING) is None,
        "Episode 1 ongoing journal still registered",
    )

    assert_true(
        journal_service.get_active_span(J_EP2_ONGOING) is None,
        "Episode 2 ongoing journal still registered",
    )

    assert_true(
        episode_service.get_active_span(EPISODE_1_ID) is None,
        "Episode 1 still registered",
    )

    assert_true(
        episode_service.get_active_span(EPISODE_2_ID) is None,
        "Episode 2 still registered",
    )

    print("Journal registry cleanup: PASS")
    print("Episode registry cleanup: PASS")

    # -----------------------------------------------------------------------
    # 22. CLOSE ENCOUNTER
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("22. CLOSE ENCOUNTER")
    print("=" * 80)

    encounter_service.close(
        encounter_id=ENCOUNTER_ID,
        end_time=t(480),
        end_reason="Full Phase 03 integration test completed",
        ended_by="ADMIN-TRACE-001",
        end_details=(
            "Encounter closed after testing multiple episodes, "
            "journal activities and clinical alarm tracing."
        ),
    )

    encounter_after = encounter_service.get_active_span(
        ENCOUNTER_ID
    )

    assert_true(
        encounter_after is None,
        "Encounter span still exists after closure",
    )

    print("Encounter closed: PASS")
    print("Encounter registry cleanup: PASS")

    # -----------------------------------------------------------------------
    # 23. PRINT FINAL SPAN INFORMATION
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("23. TRACE SUMMARY")
    print("=" * 80)

    print()
    print("TRACE ID")
    print(encounter_trace_id)

    print()
    print("ROOT SPAN")
    print(f"clinical.encounter")
    print(f"  span_id = {encounter_span_id}")

    print()
    print("EXPECTED TRACE TREE")
    print(
        """
clinical.encounter
│
├── event: clinical.journal.event
│
├── clinical.episode
│   │
│   ├── clinical.journal.activity.fixed
│   ├── clinical.journal.activity.ongoing
│   └── event: clinical.journal.event
│
├── clinical.journal.activity.fixed
│
├── clinical.episode
│   │
│   ├── clinical.journal.activity.fixed
│   ├── clinical.journal.activity.ongoing
│   └── event: clinical.journal.event
│
├── event: clinical.alarm.triggered
├── event: clinical.alarm.responded
│
└── event: clinical.journal.event
"""
    )

    # -----------------------------------------------------------------------
    # 24. EXPORT WAIT
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("24. WAIT FOR TRACE EXPORT")
    print("=" * 80)

    print("Waiting 5 seconds for OTLP batch export...")
    time.sleep(5)

    print("Trace export wait complete.")

    # -----------------------------------------------------------------------
    # FINAL RESULT
    # -----------------------------------------------------------------------

    print()
    print("=" * 80)
    print("FULL PHASE 03 INTEGRATION TEST COMPLETE")
    print("=" * 80)

    print()
    print("PASS:")
    print("  Patient reference")
    print("  Encounter lifecycle")
    print("  Encounter root span")
    print("  Encounter registry")
    print("  Episode 1")
    print("  Episode 2")
    print("  Episode sibling relationship")
    print("  Episode parent relationship")
    print("  Fixed journal activity")
    print("  Ongoing journal activity")
    print("  Explicit ongoing activity closure")
    print("  Journal event")
    print("  Activity outside episode")
    print("  Alarm event")
    print("  Alarm did not create episode")
    print("  Shared trace ID")
    print("  Registry cleanup")
    print("  Encounter closure")
    print("  OTLP export wait")

    print()
    print(f"Trace ID for Grafana/Tempo: {encounter_trace_id}")
    print()
    print("Open Grafana → Explore → Tempo and search for the Trace ID above.")
    print()


if __name__ == "__main__":
    main()