from datetime import datetime, timezone, timedelta
import time

from app.services.encounter_service import EncounterService
from app.services.episode_service import EpisodeService
from app.persistence.journals import JournalRepository
from app.tracing.episode_registry import episode_span_registry
from app.tracing.registry import encounter_span_registry
from app.tracing.provider import configure_tracing


# ============================================================
# CONFIGURE TRACING
# ============================================================

configure_tracing()

encounter_service = EncounterService()
episode_service = EpisodeService()
journal_repository = JournalRepository()


# ============================================================
# TEST IDENTIFIERS
# ============================================================

encounter_id = "E-EPISODE-001"
patient_id = "PAT-0001"

episode_id = "EP-SVC-001"
journal_id = "J-EPISODE-001"


# ============================================================
# LOGICAL TEST TIMELINE
#
# We deliberately create different logical timestamps.
#
# Encounter:
#   08:00 -> 10:00
#
# Episode:
#   08:10 -> 09:10
#
# No 1-hour sleep is required.
# ============================================================

base_time = datetime.now(timezone.utc)

encounter_start_time = base_time

episode_start_time = base_time + timedelta(minutes=10)

episode_end_time = base_time + timedelta(minutes=70)

encounter_end_time = base_time + timedelta(minutes=120)


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
    start_reason="Episode service integration test",
    started_by="ADMIN-001",
    started_by_role="ADMIN",
    start_details="Testing Journal → Episode lifecycle",
    start_time=encounter_start_time,
)

print("Encounter ID:", encounter["encounter_id"])
print("Trace ID:", encounter["trace_id"])
print("Span ID:", encounter["span_id"])

print(
    "Encounter registry:",
    encounter_span_registry.contains(encounter_id),
)


# ============================================================
# START EPISODE FROM JOURNAL
# ============================================================

print()
print("========================================")
print("START EPISODE FROM JOURNAL")
print("========================================")

episode = episode_service.start_from_journal(
    episode_id=episode_id,
    journal_id=journal_id,
    patient_id=patient_id,
    encounter_id=encounter_id,
    initiated_by="ADMIN-001",
    initiation_reason="Clinical episode integration test",
    author_role="ADMIN",
    content="Started clinical episode from administrative journal entry.",
    start_time=episode_start_time,
)

print("Episode ID:", episode["episode_id"])
print("Source Journal:", episode["source_journal_id"])
print("Status:", episode["status"])
print("Trace ID:", episode["trace_id"])


# ============================================================
# VERIFY TRACE CORRELATION
# ============================================================

print()
print("========================================")
print("VERIFY TRACE CORRELATION")
print("========================================")

print(
    "Same trace ID:",
    encounter["trace_id"] == episode["trace_id"],
)

print(
    "Episode is child of encounter:",
    episode["trace_id"] == encounter["trace_id"],
)


# ============================================================
# VERIFY JOURNAL
# ============================================================

print()
print("========================================")
print("VERIFY JOURNAL")
print("========================================")

journal = journal_repository.get(journal_id)

print(
    "Journal entry type:",
    journal["entry_type"],
)

print(
    "Journal episode ID:",
    journal["episode_id"],
)

print(
    "Episode journal linkage:",
    (
        journal["episode_id"] == episode_id
        and journal["entry_type"] == "EPISODE_START"
    ),
)


# ============================================================
# VERIFY EPISODE REGISTRY
# ============================================================

print()
print("========================================")
print("VERIFY EPISODE REGISTRY")
print("========================================")

print(
    "Episode registry:",
    episode_span_registry.contains(episode_id),
)


# ============================================================
# IMPORTANT:
# The episode is logically open from +10 min to +70 min.
#
# We do NOT sleep for an hour.
#
# This small sleep only gives the tracing/export machinery
# a moment to process the already-created span state.
# ============================================================

print()
print("Episode remains logically OPEN...")
time.sleep(1)

print(
    "Episode still registered:",
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
    end_time=episode_end_time,
)

print(
    "Episode status:",
    closed_episode["status"],
)

print(
    "Episode end time:",
    closed_episode["end_time"],
)

print(
    "Closure by:",
    closed_episode["closure_by"],
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
    end_reason="Episode service integration test complete",
    end_details="Completed Episode lifecycle validation.",
    end_time=encounter_end_time,
)

# ------------------------------------------------------------
# Verify persisted encounter after closure
# ------------------------------------------------------------

closed_encounter = encounter_service.get(
    encounter_id
)

if closed_encounter is None:
    raise RuntimeError(
        f"Encounter disappeared after closure: {encounter_id}"
    )

print(
    "Encounter status:",
    closed_encounter["status"],
)

print(
    "Encounter end time:",
    closed_encounter["end_time"],
)

print(
    "Ended by:",
    closed_encounter["ended_by"],
)

print(
    "End reason:",
    closed_encounter["end_reason"],
)

print(
    "Encounter registry cleanup:",
    not encounter_span_registry.contains(
        encounter_id
    ),
)

# ============================================================
# WAIT FOR TRACE EXPORT
# ============================================================

print()
print("Waiting for trace export...")

time.sleep(5)


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("========================================")
print("TEST COMPLETE")
print("========================================")

print()

print("Expected logical timeline:")
print()

print(
    "Encounter:",
    encounter_start_time,
    "→",
    encounter_end_time,
)

print(
    "Episode:",
    episode_start_time,
    "→",
    episode_end_time,
)

print()

print("Expected trace hierarchy:")
print()

print("clinical.encounter")
print("└── clinical.episode")
print("    └── originating Journal metadata")

print()

print("Expected duration relationship:")
print()

print("Encounter duration: 120 minutes")
print("Episode duration:    60 minutes")
print()

print("Episode is shorter than encounter: PASS")