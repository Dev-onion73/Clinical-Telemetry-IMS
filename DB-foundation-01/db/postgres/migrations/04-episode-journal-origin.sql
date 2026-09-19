-- ============================================================
-- Phase 03
-- Episode / Journal provenance migration
--
-- Current architecture:
--
--     Journal
--        |
--        | START_EPISODE
--        v
--     Episode
--
-- Historical Episodes are retained.
-- Their source_journal_id remains NULL because their original
-- Journal provenance cannot be established from existing data.
--
-- New Episodes MUST be created through a Journal.
-- That invariant is enforced by EpisodeService.
-- ============================================================


-- ============================================================
-- 1. JOURNAL ENTRY TYPE
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'journal_entry_type'
    ) THEN

        CREATE TYPE journal_entry_type AS ENUM (
            'EVENT',
            'FIXED_ACTIVITY',
            'ONGOING_ACTIVITY',
            'EPISODE_START'
        );

    END IF;
END
$$;


-- ============================================================
-- 2. JOURNAL ENTRY TYPE COLUMN
-- ============================================================

ALTER TABLE journals
ADD COLUMN IF NOT EXISTS entry_type journal_entry_type
NOT NULL DEFAULT 'EVENT';


-- ============================================================
-- 3. JOURNAL → EPISODE REFERENCE
-- ============================================================

ALTER TABLE journals
ADD COLUMN IF NOT EXISTS episode_id character varying(64);


-- ============================================================
-- 4. EPISODE → SOURCE JOURNAL
--
-- Nullable intentionally.
--
-- Existing historical Episodes do not have reliable Journal
-- provenance and therefore cannot be backfilled honestly.
-- ============================================================

ALTER TABLE episodes
ADD COLUMN IF NOT EXISTS source_journal_id character varying(64);


-- ============================================================
-- 5. EPISODE INITIATION REASON
-- ============================================================

ALTER TABLE episodes
ADD COLUMN IF NOT EXISTS initiation_reason text;


-- ============================================================
-- 6. REMOVE STALE PAGING / INCIDENT ORIGIN
--
-- IncidentRelay is no longer part of the architecture.
-- ============================================================

DROP INDEX IF EXISTS idx_episodes_source_paging_incident;

ALTER TABLE episodes
DROP COLUMN IF EXISTS source_paging_incident_id;


-- ============================================================
-- 7. REMOVE STALE INITIATION METHOD
--
-- Episodes are no longer created through:
--
--     ALARM
--     MANUAL
--     SCHEDULED_PROCEDURE
--     UNPLANNED_PROCEDURE
--     OTHER
--
-- New Episode creation is exclusively Journal-driven.
-- ============================================================

ALTER TABLE episodes
DROP COLUMN IF EXISTS initiation_method;


-- ============================================================
-- 8. EPISODE → SOURCE JOURNAL FOREIGN KEY
-- ============================================================

ALTER TABLE episodes
ADD CONSTRAINT fk_episode_source_journal
FOREIGN KEY (source_journal_id)
REFERENCES journals(journal_id);


-- ============================================================
-- 9. JOURNAL → EPISODE FOREIGN KEY
-- ============================================================

ALTER TABLE journals
ADD CONSTRAINT fk_journal_episode
FOREIGN KEY (episode_id)
REFERENCES episodes(episode_id);


-- ============================================================
-- 10. INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_journals_episode_id
ON journals(episode_id);

CREATE INDEX IF NOT EXISTS idx_episodes_source_journal_id
ON episodes(source_journal_id);


-- ============================================================
-- 11. DOCUMENT HISTORICAL MIGRATION
--
-- Existing rows intentionally remain NULL in source_journal_id.
--
-- We do NOT fabricate Journal provenance.
-- ============================================================

UPDATE episodes
SET initiation_reason =
    'Legacy Episode migrated from Phase 01 seed data; original Journal provenance unavailable.'
WHERE initiation_reason IS NULL;


-- ============================================================
-- END
-- ============================================================