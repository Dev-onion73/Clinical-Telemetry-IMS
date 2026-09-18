-- ============================================================
-- Healthcare Incident Management
-- Phase 01 — Foundation Database
-- Seed Data
-- ============================================================

-- ============================================================
-- PATIENTS
-- ============================================================

INSERT INTO patients (
    patient_id,
    first_name,
    last_name,
    date_of_birth,
    sex,
    blood_group
)
VALUES
    (
        'PAT-0001',
        'Arun',
        'Kumar',
        '1998-04-12',
        'MALE',
        'B_POSITIVE'
    ),
    (
        'PAT-0002',
        'Priya',
        'Sharma',
        '1995-09-23',
        'FEMALE',
        'O_POSITIVE'
    ),
    (
        'PAT-0003',
        'Rahul',
        'Menon',
        '1989-01-17',
        'MALE',
        'A_NEGATIVE'
    );

-- ============================================================
-- ENCOUNTERS
-- ============================================================

INSERT INTO encounters (
    encounter_id,
    patient_id,
    encounter_type,
    care_setting,
    status,
    start_time,
    end_time
)
VALUES
    (
        'E1',
        'PAT-0001',
        'EMERGENCY',
        'EMERGENCY',
        'CLOSED',
        '2026-08-05 08:00:00+00',
        '2026-08-05 16:30:00+00'
    ),
    (
        'E2',
        'PAT-0001',
        'FOLLOW_UP',
        'OUTPATIENT',
        'CLOSED',
        '2026-08-12 10:00:00+00',
        '2026-08-12 11:00:00+00'
    ),
    (
        'E3',
        'PAT-0002',
        'ROUTINE',
        'OUTPATIENT',
        'CLOSED',
        '2026-08-06 09:00:00+00',
        '2026-08-06 10:30:00+00'
    ),
    (
        'E4',
        'PAT-0003',
        'PROCEDURE',
        'INPATIENT',
        'CLOSED',
        '2026-08-07 07:30:00+00',
        '2026-08-07 14:00:00+00'
    );

-- ============================================================
-- EPISODES
-- ============================================================

INSERT INTO episodes (
    episode_id,
    patient_id,
    encounter_id,
    trace_id,
    initiated_by,
    initiation_method,
    source_paging_incident_id,
    status,
    start_time,
    end_time,
    closure_by,
    closure_time
)
VALUES
    (
        'E1_EP1',
        'PAT-0001',
        'E1',
        NULL,
        'DR-RAJESH',
        'ALARM',
        NULL,
        'CLOSED',
        '2026-08-05 08:10:00+00',
        '2026-08-05 08:20:00+00',
        'DR-RAJESH',
        '2026-08-05 08:20:00+00'
    ),
    (
        'E2_EP1',
        'PAT-0001',
        'E2',
        NULL,
        'DR-RAJESH',
        'SCHEDULED_PROCEDURE',
        NULL,
        'CLOSED',
        '2026-08-12 10:15:00+00',
        '2026-08-12 10:45:00+00',
        'DR-RAJESH',
        '2026-08-12 10:45:00+00'
    ),
    (
        'E3_EP1',
        'PAT-0002',
        'E3',
        NULL,
        'DR-MEERA',
        'MANUAL',
        NULL,
        'CLOSED',
        '2026-08-06 09:20:00+00',
        '2026-08-06 09:45:00+00',
        'DR-MEERA',
        '2026-08-06 09:45:00+00'
    ),
    (
        'E4_EP1',
        'PAT-0003',
        'E4',
        NULL,
        'DR-ARUN',
        'SCHEDULED_PROCEDURE',
        NULL,
        'CLOSED',
        '2026-08-07 08:00:00+00',
        '2026-08-07 13:30:00+00',
        'DR-ARUN',
        '2026-08-07 13:30:00+00'
    );

-- ============================================================
-- JOURNALS
-- ============================================================

INSERT INTO journals (
    journal_id,
    patient_id,
    encounter_id,
    author_id,
    author_role,
    timestamp,
    content
)
VALUES
    (
        'JRN-0001',
        'PAT-0001',
        'E1',
        'NURSE-ANITHA',
        'NURSE',
        '2026-08-05 08:05:00+00',
        'Patient arrived at emergency department. Initial assessment initiated.'
    ),
    (
        'JRN-0002',
        'PAT-0001',
        'E1',
        'DR-RAJESH',
        'PHYSICIAN',
        '2026-08-05 08:14:00+00',
        'Patient developed rash following medication exposure. SpO2 decreased and allergic reaction suspected. Epinephrine administered.'
    ),
    (
        'JRN-0003',
        'PAT-0001',
        'E1',
        'NURSE-ANITHA',
        'NURSE',
        '2026-08-05 08:18:00+00',
        'Patient monitored following intervention. Respiratory status improving.'
    ),
    (
        'JRN-0004',
        'PAT-0002',
        'E3',
        'DR-MEERA',
        'PHYSICIAN',
        '2026-08-06 09:15:00+00',
        'Routine clinical assessment completed. No acute concerns identified.'
    ),
    (
        'JRN-0005',
        'PAT-0003',
        'E4',
        'DR-ARUN',
        'PHYSICIAN',
        '2026-08-07 08:05:00+00',
        'Pre-procedure assessment completed and patient cleared for scheduled procedure.'
    );