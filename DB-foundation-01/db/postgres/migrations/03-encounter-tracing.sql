-- ============================================================
-- Healthcare Incident Management
-- Phase 03 — Encounter Lifecycle + Tracing
-- Migration 03
-- ============================================================

ALTER TABLE encounters
ADD COLUMN start_reason TEXT,
ADD COLUMN started_by VARCHAR(64),
ADD COLUMN start_details TEXT,

ADD COLUMN end_reason TEXT,
ADD COLUMN ended_by VARCHAR(64),
ADD COLUMN end_details TEXT,

ADD COLUMN trace_id VARCHAR(32),
ADD COLUMN span_id VARCHAR(16);

CREATE INDEX idx_encounters_trace_id
    ON encounters(trace_id);

CREATE INDEX idx_encounters_span_id
    ON encounters(span_id);