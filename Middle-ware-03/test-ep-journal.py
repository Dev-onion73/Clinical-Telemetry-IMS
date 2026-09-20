from datetime import datetime, timezone, timedelta
import time

from app.services.encounter_service import EncounterService
from app.services.episode_service import EpisodeService
from app.services.journal_service import JournalService

from app.tracing.provider import configure_tracing
from app.tracing.registry import encounter_span_registry
from app.tracing.episode_registry import episode_span_registry
from app.tracing.journal_registry import journal_span_registry


# ============================================================
# TRACING
# ============================================================

configure_tracing()

encounter_service = EncounterService()
episode_service = EpisodeService()
journal_service = JournalService()


# ============================================================
# IDS
# ============================================================

encounter_id = "E-JOURNAL-EP-001"
patient_id = "PAT-0001"

episode_id = "EP-JOURNAL-001"
episode_journal_id = "J-EPISODE-START-001"

event_id = "J-EPISODE-EVENT-001"
fixed_id = "J-EPISODE-FIXED-001"
ongoing_id = "J-EPISODE-ONGOING-001"


# ============================================================
# LOGICAL TIMELINE
# ============================================================

base_time = datetime.now(timezone.utc)

encounter_start = base_time

episode_start = (
    base_time + timedelta(minutes=10)
)

event_time = (
    base_time + timedelta(minutes=15)
)

fixed_start = (
    base_time + timedelta(minutes=20)
)

fixed_end = (
    base_time + timedelta(minutes=30)
)

ongoing_start = (
    base_time + timedelta(minutes=35)
)

ongoing_end = (
    base_time + timedelta(minutes=50)
)

episode_end = (
    base_time + timedelta(minutes=60)
)

encounter_end = (
    base_time + timedelta(minutes=90)
)


# ============================================================
# START ENCOUNTER
# ============================================================

print()
print("========================================")
print("START ENCOUNTER")
print("========================================")

encounter = encounter_service.start(
    encounter_id=encounter_id,
    patient_id=patient_id,
    encounter_type="EMERGENCY",
    care_setting="EMERGENCY",
    start_reason="Episode Journal integration test",
    started_by="ADMIN-001",
    started_by_role="ADMIN",
    start_details="Testing Journal entries inside Episode",
    start_time=encounter_start,
)

print(
    "Encounter trace:",
    encounter["trace_id"],
)

print(
    "Encounter registry:",
    encounter_span_registry.contains(
        encounter_id
    ),
)


# ============================================================
# START EPISODE
# ============================================================

print()
print("========================================")
print("START EPISODE")
print("========================================")

episode = episode_service.start_from_journal(
    episode_id=episode_id,
    journal_id=episode_journal_id,
    patient_id=patient_id,
    encounter_id=encounter_id,
    initiated_by="ADMIN-001",
    initiation_reason="Testing Episode Journal hierarchy",
    author_role="ADMIN",
    content="Started clinical episode.",
    start_time=episode_start,
)

print(
    "Episode trace:",
    episode["trace_id"],
)

print(
    "Same TraceId:",
    episode["trace_id"]
    == encounter["trace_id"],
)

print(
    "Episode registry:",
    episode_span_registry.contains(
        episode_id
    ),
)


# ============================================================
# EVENT JOURNAL INSIDE EPISODE
# ============================================================

print()
print("========================================")
print("EPISODE JOURNAL EVENT")
print("========================================")

event_journal = journal_service.create_event(
    journal_id=event_id,
    patient_id=patient_id,
    encounter_id=encounter_id,
    author_id="NURSE-001",
    author_role="NURSE",
    content="Patient reported improvement.",
    timestamp=event_time,
    episode_id=episode_id,
)

print(
    "Journal type:",
    event_journal["entry_type"],
)

print(
    "Episode ID:",
    event_journal["episode_id"],
)

print(
    "Episode linkage:",
    event_journal["episode_id"]
    == episode_id,
)


# ============================================================
# FIXED ACTIVITY INSIDE EPISODE
# ============================================================

print()
print("========================================")
print("EPISODE FIXED ACTIVITY")
print("========================================")

fixed_journal = (
    journal_service.create_fixed_activity(
        journal_id=fixed_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        author_id="NURSE-001",
        author_role="NURSE",
        content="Continuous observation performed.",
        start_time=fixed_start,
        end_time=fixed_end,
        start_reason="Observation started",
        end_reason="Observation completed",
        episode_id=episode_id,
    )
)

print(
    "Journal type:",
    fixed_journal["entry_type"],
)

print(
    "Episode ID:",
    fixed_journal["episode_id"],
)

print(
    "Episode linkage:",
    fixed_journal["episode_id"]
    == episode_id,
)


# ============================================================
# ONGOING ACTIVITY INSIDE EPISODE
# ============================================================

print()
print("========================================")
print("EPISODE ONGOING ACTIVITY")
print("========================================")

ongoing_journal = (
    journal_service.start_ongoing_activity(
        journal_id=ongoing_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        author_id="DR-RAJESH",
        author_role="PHYSICIAN",
        content="Monitoring response to intervention.",
        start_time=ongoing_start,
        start_reason="Clinical monitoring started",
        episode_id=episode_id,
    )
)

print(
    "Journal type:",
    ongoing_journal["entry_type"],
)

print(
    "Episode ID:",
    ongoing_journal["episode_id"],
)

print(
    "Episode linkage:",
    ongoing_journal["episode_id"]
    == episode_id,
)

print(
    "Ongoing registry:",
    journal_span_registry.contains(
        ongoing_id
    ),
)


# ============================================================
# END ONGOING ACTIVITY
# ============================================================

print()
print("========================================")
print("END EPISODE ONGOING ACTIVITY")
print("========================================")

journal_service.end_ongoing_activity(
    journal_id=ongoing_id,
    end_time=ongoing_end,
    end_reason="Monitoring completed",
    actor_id="DR-RAJESH",
    actor_role="PHYSICIAN",
)

print(
    "Journal registry cleanup:",
    not journal_span_registry.contains(
        ongoing_id
    ),
)


# ============================================================
# VERIFY EPISODE STILL OPEN
# ============================================================

print()
print("========================================")
print("VERIFY EPISODE")
print("========================================")

open_episode = episode_service.get(
    episode_id
)

print(
    "Episode status:",
    open_episode["status"],
)

print(
    "Episode still open:",
    open_episode["status"] == "OPEN",
)

print(
    "Episode registry:",
    episode_span_registry.contains(
        episode_id
    ),
)


# ============================================================
# CLOSE EPISODE
# ============================================================

print()
print("========================================")
print("CLOSE EPISODE")
print("========================================")

closed_episode = episode_service.close(
    episode_id=episode_id,
    closure_by="ADMIN-001",
    end_time=episode_end,
)

print(
    "Episode status:",
    closed_episode["status"],
)

print(
    "Episode registry cleanup:",
    not episode_span_registry.contains(
        episode_id
    ),
)


# ============================================================
# CLOSE ENCOUNTER
# ============================================================

print()
print("========================================")
print("CLOSE ENCOUNTER")
print("========================================")

encounter_service.close(
    encounter_id=encounter_id,
    ended_by="ADMIN-001",
    end_reason="Episode Journal test complete",
    end_details="Completed Episode-aware Journal validation.",
    end_time=encounter_end,
)

print(
    "Encounter registry cleanup:",
    not encounter_span_registry.contains(
        encounter_id
    ),
)


# ============================================================
# EXPORT
# ============================================================

print()
print("Waiting for trace export...")

time.sleep(5)


# ============================================================
# FINAL
# ============================================================

print()
print("========================================")
print("TEST COMPLETE")
print("========================================")

print()
print("Expected hierarchy:")
print()
print("clinical.encounter")
print("├── clinical.episode")
print("│   ├── event: clinical.journal.event")
print("│   ├── clinical.journal.activity")
print("│   └── clinical.journal.activity")
print("└── other encounter-level journal entries")
print()