-- ============================================================
-- Healthcare Incident Management
-- Phase 01 — Foundation Database
-- PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE sex_type AS ENUM (
    'MALE',
    'FEMALE',
    'OTHER',
    'UNKNOWN'
);

CREATE TYPE blood_group_type AS ENUM (
    'A_POSITIVE',
    'A_NEGATIVE',
    'B_POSITIVE',
    'B_NEGATIVE',
    'AB_POSITIVE',
    'AB_NEGATIVE',
    'O_POSITIVE',
    'O_NEGATIVE',
    'UNKNOWN'
);

CREATE TYPE encounter_type AS ENUM (
    'EMERGENCY',
    'ROUTINE',
    'FOLLOW_UP',
    'PROCEDURE',
    'OTHER'
);

CREATE TYPE care_setting_type AS ENUM (
    'INPATIENT',
    'OUTPATIENT',
    'EMERGENCY'
);

CREATE TYPE encounter_status AS ENUM (
    'OPEN',
    'ACTIVE',
    'CLOSED'
);

CREATE TYPE episode_initiation_method AS ENUM (
    'ALARM',
    'MANUAL',
    'SCHEDULED_PROCEDURE',
    'UNPLANNED_PROCEDURE',
    'OTHER'
);

CREATE TYPE episode_status AS ENUM (
    'OPEN',
    'ACTIVE',
    'CLOSED'
);

-- ============================================================
-- PATIENTS
-- ============================================================

CREATE TABLE patients (
    patient_id      VARCHAR(64) PRIMARY KEY,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    date_of_birth   DATE NOT NULL,
    sex             sex_type NOT NULL DEFAULT 'UNKNOWN',
    blood_group     blood_group_type NOT NULL DEFAULT 'UNKNOWN',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ENCOUNTERS
-- ============================================================

CREATE TABLE encounters (
    encounter_id    VARCHAR(64) PRIMARY KEY,
    patient_id      VARCHAR(64) NOT NULL,

    encounter_type  encounter_type NOT NULL,
    care_setting    care_setting_type NOT NULL,
    status          encounter_status NOT NULL DEFAULT 'OPEN',

    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_encounter_patient
        FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id),

    CONSTRAINT chk_encounter_time
        CHECK (end_time IS NULL OR end_time >= start_time),

    CONSTRAINT chk_closed_encounter_end_time
        CHECK (
            status <> 'CLOSED'
            OR end_time IS NOT NULL
        )
);

CREATE INDEX idx_encounters_patient_id
    ON encounters(patient_id);

CREATE INDEX idx_encounters_status
    ON encounters(status);

CREATE INDEX idx_encounters_start_time
    ON encounters(start_time);

-- ============================================================
-- EPISODES
-- ============================================================

CREATE TABLE episodes (
    episode_id                  VARCHAR(64) PRIMARY KEY,

    patient_id                  VARCHAR(64) NOT NULL,
    encounter_id                VARCHAR(64) NOT NULL,

    -- Populated when the corresponding Tempo trace exists.
    trace_id                    VARCHAR(256),

    initiated_by                VARCHAR(64),
    initiation_method           episode_initiation_method NOT NULL,

    -- Populated only when the episode originated from
    -- an IncidentRelay paging incident.
    source_paging_incident_id   VARCHAR(256),

    status                      episode_status NOT NULL DEFAULT 'OPEN',

    start_time                  TIMESTAMPTZ NOT NULL,
    end_time                    TIMESTAMPTZ,

    closure_by                  VARCHAR(64),
    closure_time                TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_episode_patient
        FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id),

    CONSTRAINT fk_episode_encounter
        FOREIGN KEY (encounter_id)
        REFERENCES encounters(encounter_id),

    CONSTRAINT chk_episode_time
        CHECK (end_time IS NULL OR end_time >= start_time),

    CONSTRAINT chk_closed_episode_end_time
        CHECK (
            status <> 'CLOSED'
            OR end_time IS NOT NULL
        ),

    CONSTRAINT chk_closed_episode_closure
        CHECK (
            status <> 'CLOSED'
            OR (
                closure_by IS NOT NULL
                AND closure_time IS NOT NULL
            )
        )
);

CREATE INDEX idx_episodes_patient_id
    ON episodes(patient_id);

CREATE INDEX idx_episodes_encounter_id
    ON episodes(encounter_id);

CREATE INDEX idx_episodes_status
    ON episodes(status);

CREATE INDEX idx_episodes_start_time
    ON episodes(start_time);

CREATE INDEX idx_episodes_trace_id
    ON episodes(trace_id);

CREATE INDEX idx_episodes_source_paging_incident
    ON episodes(source_paging_incident_id);

-- ============================================================
-- JOURNALS
-- ============================================================

CREATE TABLE journals (
    journal_id      VARCHAR(64) PRIMARY KEY,

    patient_id      VARCHAR(64) NOT NULL,
    encounter_id    VARCHAR(64) NOT NULL,

    author_id       VARCHAR(64) NOT NULL,
    author_role     VARCHAR(100) NOT NULL,

    -- Clinical/documentation timestamp.
    timestamp       TIMESTAMPTZ NOT NULL,

    content         TEXT NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_journal_patient
        FOREIGN KEY (patient_id)
        REFERENCES patients(patient_id),

    CONSTRAINT fk_journal_encounter
        FOREIGN KEY (encounter_id)
        REFERENCES encounters(encounter_id)
);

CREATE INDEX idx_journals_patient_id
    ON journals(patient_id);

CREATE INDEX idx_journals_encounter_id
    ON journals(encounter_id);

CREATE INDEX idx_journals_timestamp
    ON journals(timestamp);

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_patients_updated_at
BEFORE UPDATE ON patients
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_encounters_updated_at
BEFORE UPDATE ON encounters
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_episodes_updated_at
BEFORE UPDATE ON episodes
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_journals_updated_at
BEFORE UPDATE ON journals
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();