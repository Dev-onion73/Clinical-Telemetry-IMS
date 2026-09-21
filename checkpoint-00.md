Yes. Here is the **current canonical project summary**, incorporating the latest correction that **Grafana alerts and clinical alarms are the same alarm object in our domain**, with InfluxDB as the source of the monitored vitals.

# Healthcare Incident Management — Complete Project Context & Current State

## 1. Project objective

The project is a **clinical observability and incident-management platform** inspired by concepts from IT observability, but adapted to healthcare.

The central idea is to connect:

```text
Patient
  │
  ├── continuous vitals ──────────────► InfluxDB
  │                                        │
  │                                        ▼
  │                                     Grafana
  │                                        │
  │                                  Alert condition
  │                                        │
  │                                        ▼
  │                                      ALARM
  │                                        │
  │                                        ▼
  │                                Clinical Middleware
  │                                        │
  │                         ┌──────────────┼──────────────┐
  │                         ▼              ▼              ▼
  │                      Journal        Episode        Trace
  │                         │              │              │
  └─────────────────────────┴──────────────┴──────────────┘
```

The system deliberately separates three different types of clinical information:

| Concept        | Purpose                                         | Main storage                 |
| -------------- | ----------------------------------------------- | ---------------------------- |
| **Metrics**    | Continuous/high-volume patient measurements     | InfluxDB                     |
| **Journals**   | Human clinical documentation/actions            | PostgreSQL                   |
| **Traces**     | Timeline/hierarchy of an encounter              | Tempo                        |
| **Alarms**     | Alert instances generated from monitored vitals | PostgreSQL + Trace event     |
| **Episodes**   | Clinically meaningful intervals                 | PostgreSQL + Trace span      |
| **Encounters** | Complete patient interaction                    | PostgreSQL + root trace span |

The goal is not simply to create a hospital database. The goal is to create a **time-oriented clinical observability system** where a patient's encounter can be understood as a trace.

---

# 2. Core conceptual model

The most important distinction we have established is:

### Encounter

The **root clinical interaction**.

Example:

```text
Patient arrives in emergency department
        ↓
Encounter E1
        ↓
08:00 ───────────────────── 16:30
```

The encounter becomes the root OpenTelemetry span:

```text
clinical.encounter
```

---

### Episode

An episode is a **meaningful clinical interval inside an encounter**.

It is not automatically created by an alarm.

Example:

```text
Encounter
08:00 ─────────────────────────────────── 16:30

          Episode: Emergency Assessment
          08:00 ─────── 08:20
```

An episode therefore becomes a child span of the encounter:

```text
clinical.encounter
└── clinical.episode
```

---

### Journal

A journal is a human-originated clinical record.

We have four conceptual journal modes:

```text
EVENT
FIXED_ACTIVITY
ONGOING_ACTIVITY
EPISODE
```

Their tracing behavior is different.

#### EVENT

A point-in-time journal action.

It becomes a **span event**, not a separate span.

```text
clinical.encounter
    │
    └── event: clinical.journal.event
```

#### FIXED_ACTIVITY

A completed activity with start and end.

```text
clinical.encounter
└── clinical.journal.activity
```

or, if associated with an episode:

```text
clinical.encounter
└── clinical.episode
    └── clinical.journal.activity
```

#### ONGOING_ACTIVITY

An activity that remains open.

```text
clinical.encounter
└── clinical.journal.activity
       08:10 ────────────────>
```

It must **not automatically terminate after some timeout**.

It remains registered until explicitly closed.

#### EPISODE

A special journal action used by staff/admin to initiate a clinical episode.

```text
Staff/Admin
    │
    ▼
Journal: EPISODE
    │
    ▼
Episode record
    │
    ▼
clinical.episode span
```

---

# 3. Alarm model — important correction

We have now settled this:

> **Grafana alert instance = clinical alarm.**

There is no separate IncidentRelay layer.

The flow is:

```text
Patient vitals
     │
     ▼
InfluxDB
     │
     ▼
Grafana alert rule
     │
     │ condition triggered
     ▼
Clinical Alarm
     │
     ├── triggered
     ├── responded
     ├── dismissed
     └── unanswered
```

So:

* InfluxDB contains the continuous measurements.
* Grafana evaluates those measurements.
* A fired Grafana alert is our **clinical alarm**.
* The middleware receives/handles that alarm.
* The alarm does **not** create an episode automatically.

This is consistent with the observability stack: Grafana/Tempo can integrate metrics, logs and traces, while Tempo receives trace data through OTLP. ([Grafana Labs][1])

---

# 4. What creates an episode?

This is now an important rule.

### Primary source

**Staff/admin journal → `EPISODE`**

```text
Staff/Admin
    │
    ▼
EPISODE journal
    │
    ▼
Episode
```

### Procedure/workflow sources

The database currently also has concepts for:

```text
SCHEDULED_PROCEDURE
UNPLANNED_PROCEDURE
OTHER
```

These can represent workflow-driven episode initiation if we retain them in the final model.

### What does NOT create an episode?

```text
InfluxDB abnormal vital
        ↓
Grafana alert
        ↓
Alarm
```

does **not** automatically become:

```text
Episode
```

Instead:

```text
InfluxDB
   ↓
Grafana
   ↓
Alarm
   ↓
staff/admin response
```

The clinician may subsequently decide to initiate an episode.

---

# 5. Trace hierarchy

Our intended hierarchy is:

## Encounter without an episode

```text
clinical.encounter
│
├── event: clinical.journal.event
│
├── clinical.journal.activity
│
├── clinical.journal.activity
│
└── event: clinical.alarm
```

Here:

* EVENT journal = event
* FIXED_ACTIVITY = sibling span
* ONGOING_ACTIVITY = sibling span
* alarm = point event

OpenTelemetry explicitly models spans as operations that can form a trace tree, and spans can contain timestamped events. ([OpenTelemetry][2])

---

## Encounter with an episode

```text
clinical.encounter
│
├── clinical.episode
│   │
│   ├── clinical.journal.activity
│   │
│   ├── clinical.journal.activity
│   │
│   └── event: clinical.alarm
│
├── clinical.journal.activity
│
└── event: clinical.journal.event
```

The rule is:

> **A span belongs either directly to the encounter or to the episode when it is episode-associated.**

We do **not** make journal activities children of other journal activities.

---

# 6. Alarm tracing

An alarm is fundamentally a point event.

For example:

```text
clinical.encounter
        │
        ├── event: clinical.alarm.triggered
        │       alarm_id=ALARM-001
        │       severity=CRITICAL
        │       spo2=82
        │       source=grafana
        │
        └── event: clinical.alarm.responded
                responder=STAFF-001
                response_latency=42s
```

If we later need a visible duration bar for the response lifecycle, we can derive an optional alarm-response span.

But the **source domain object remains the alarm**, not an episode.

---

# 7. Phase 00 — Grafana

### Status: Completed

Grafana was established as the visualization/observability layer.

It is connected to:

```text
PostgreSQL
InfluxDB
Tempo
```

The eventual role is:

```text
InfluxDB
   ↓
Grafana dashboards
   ↓
Grafana alert rules
   ↓
Clinical alarms
```

Grafana is therefore not merely a dashboard anymore. It is also the alert-generation point for the clinical alarm workflow.

---

# 8. Phase 01 — Database foundation

### Status: Completed

We created the clinical data foundation using:

```text
PostgreSQL
InfluxDB
```

with a shared Docker network:

```text
clinical-net
```

---

## PostgreSQL

The major tables are:

```text
patients
encounters
episodes
journals
```

### patients

Stores patient identity/basic clinical information.

Fields include:

```text
patient_id
first_name
last_name
date_of_birth
sex
blood_group
created_at
updated_at
```

---

### encounters

Stores the lifecycle of the patient's encounter.

Original fields include:

```text
encounter_id
patient_id
encounter_type
care_setting
status
start_time
end_time
created_at
updated_at
```

Phase 03 added:

```text
start_reason
started_by
start_details

end_reason
ended_by
end_details

trace_id
span_id
```

and indexes for:

```text
trace_id
span_id
```

This lets PostgreSQL correlate the clinical encounter with Tempo.

---

### episodes

Current structure:

```text
episode_id
patient_id
encounter_id
trace_id
initiated_by
initiation_method
source_paging_incident_id
status
start_time
end_time
closure_by
closure_time
created_at
updated_at
```

There are also indexes on:

```text
patient_id
encounter_id
status
start_time
trace_id
source_paging_incident_id
```

### Important technical debt

The current PostgreSQL enum still contains:

```text
ALARM
```

as an episode initiation method.

That is now conceptually outdated.

We should eventually migrate it because:

> **Alarm ≠ episode source.**

---

### journals

Current table:

```text
journal_id
patient_id
encounter_id
author_id
author_role
timestamp
content
created_at
updated_at
```

Currently it does **not yet persist `journal_type`**.

That is one of the schema pieces we still need to decide and probably migrate for the completed Phase 03 design.

---

# 9. InfluxDB

InfluxDB stores continuous vitals.

Measurement:

```text
vitals
```

Tags:

```text
patient_id
encounter_id
device_id
```

Fields:

```text
spo2
heart_rate
temperature
respiratory_rate
systolic_bp
diastolic_bp
```

This creates the continuous metric stream:

```text
patient
   ↓
device
   ↓
InfluxDB
   ↓
Grafana
```

---

# 10. Phase 02 — tracing foundation

### Status: Completed

We built:

```text
Tempo
OpenTelemetry Collector
OpenTelemetry SDK
Grafana Tempo datasource
```

The current tracing pipeline is:

```text
Clinical Middleware
       │
       ▼
OpenTelemetry SDK
       │
       ▼
OTLP
       │
       ▼
OpenTelemetry Collector
       │
       ▼
Tempo
       │
       ▼
Grafana
```

The OpenTelemetry Collector architecture is explicitly receiver → processor → exporter, which is the pattern used in our configuration. ([Grafana Labs][3])

Tempo supports OTLP ingestion and Grafana has native Tempo integration. ([Grafana Labs][1])

---

# 11. Current Tempo configuration

We have:

```text
Tempo
  HTTP: 3200
  OTLP gRPC: 4317
  OTLP HTTP: 4318
```

and the Collector exposes:

```text
host 4319 → collector 4317
host 4320 → collector 4318
```

Collector receives OTLP and exports to:

```text
clinical-tempo:4317
```

The development environment uses insecure gRPC between Collector and Tempo.

Tempo's current documentation confirms OTLP gRPC on 4317 and OTLP HTTP on 4318 as the standard configured receivers, while TLS should be used for production. ([Grafana Labs][3])

---

# 12. Important tracing bug we solved

Initially:

```text
Span.end(end_time=datetime)
```

caused:

```text
TypeError:
'datetime.datetime' object cannot be interpreted as an integer
```

The OpenTelemetry API expected nanoseconds.

We fixed it using:

```python
int(dt.timestamp() * 1_000_000_000)
```

After that, traces successfully exported to Tempo.

---

# 13. Phase 03 — Clinical Middleware

### Current phase

This is where we are now.

Directory:

```text
Middle-ware-03/
└── app/
    ├── services/
    │   ├── alarm_service.py
    │   ├── encounter_service.py
    │   ├── episode_service.py
    │   ├── journal_service.py
    │   └── trace_service.py
    │
    └── tracing/
        ├── context.py
        ├── exporter.py
        ├── provider.py
        └── registry.py
```

The middleware is intended to become the **business/orchestration layer** connecting:

```text
PostgreSQL
InfluxDB
Grafana
Tempo
Staff/Admin workflows
Grafana alarms
```

---

# 14. Encounter implementation achieved

We have implemented encounter lifecycle logic.

The basic flow is:

```text
patient exists
     ↓
EncounterService.start()
     ↓
PostgreSQL encounter
     ↓
clinical.encounter span
     ↓
trace_id + span_id
     ↓
registry
```

Then:

```text
EncounterService.close()
     ↓
end encounter span
     ↓
persist end metadata
     ↓
remove from registry
```

We also established that a new patient should conceptually be:

```text
1. Create patient
2. Start encounter
3. Create root trace span
```

---

# 15. Encounter tracing test passed

We proved:

```text
Encounter
    │
    └── root span
```

and that the registry contains the active encounter span.

The PostgreSQL repository was also tested independently.

Repository persistence successfully returned the encounter with its expected fields.

---

# 16. Registry implementation

We implemented an in-memory registry for active spans.

It currently handles:

```text
Encounter spans
Ongoing journal activity spans
```

The registry test proved:

```text
start encounter
     ↓
registry contains encounter
     ↓
retrieve same Span object
     ↓
create child journal span
     ↓
trace IDs match
     ↓
parent span ID matches encounter
     ↓
end encounter
     ↓
registry cleanup
```

This passed.

### Production consideration

This registry is currently process-local.

That is fine for our current single-process testing.

Later, if HTTP/API and scheduler/workers are separated into different processes, an in-memory registry cannot be treated as globally shared state. That becomes a production architecture issue.

We should **not solve that prematurely**.

---

# 17. Journal implementation achieved

We successfully tested:

### EVENT

```text
J-EVENT-001
```

Persisted successfully.

Conceptually:

```text
clinical.encounter
└── event: clinical.journal.event
```

---

### FIXED_ACTIVITY

```text
J-FIXED-001
```

Persisted successfully and represented as a completed child span.

---

### ONGOING_ACTIVITY

```text
J-ONGOING-001
```

Successfully:

```text
opened
↓
registered
↓
kept active
↓
explicitly closed
↓
registry cleaned
```

The important correction we made:

> An ongoing activity must not automatically terminate after five seconds.

The previous 5-second test was only the test script closing it after waiting.

The correct semantics are:

```text
START ONGOING
      │
      ▼
OPEN SPAN
      │
      │  remains open
      │
      │
      ▼
EXPLICIT CLOSE
      │
      ▼
END SPAN
```

---

# 18. Successful journal integration test

The test demonstrated:

```text
=== START ENCOUNTER ===
Encounter: E-JOURNAL-001
Trace ID: 9514e6dff058ff714d07c95c29016561
Encounter Span ID: fdb60f542b05b0ea
Encounter registry: PASS

=== CREATE JOURNAL EVENT ===
Journal ID: J-EVENT-001
Journal type: EVENT
Event persisted: PASS

=== CREATE FIXED ACTIVITY ===
Journal ID: J-FIXED-001
Journal type: FIXED_ACTIVITY
Fixed activity persisted: PASS

=== START ONGOING ACTIVITY ===
Journal ID: J-ONGOING-001
Journal type: ONGOING_ACTIVITY
Ongoing span registry: PASS

=== END ONGOING ACTIVITY ===
Ongoing activity closed: PASS
Journal registry cleanup: PASS

=== VERIFY ENCOUNTER ===
Encounter remains open: PASS

=== CLOSE ENCOUNTER ===
Encounter closed: PASS
Encounter registry cleanup: PASS
```

This is an important milestone.

We have proven the basic:

```text
Encounter
  +
Journal
  +
OpenTelemetry
  +
PostgreSQL
  +
Tempo
```

integration.

---

# 19. Current trace structure proven

The basic trace we have already demonstrated is:

```text
clinical.encounter
├── clinical.journal.activity
└── clinical.journal.activity
```

with journal events attached as events rather than incorrectly creating spans.

This matches the OpenTelemetry trace model, where a span can contain timestamped events and nested spans form the trace tree. ([OpenTelemetry][2])

---

# 20. What has NOT been completed yet

This is the important part.

We are **not finished with Phase 03**.

The remaining major work is:

### A. Finish episode tracing

Currently:

```text
episode_service.py
```

exists, but the full episode → trace implementation still needs to be completed and tested.

We need:

```text
EPISODE journal
       ↓
PostgreSQL episode
       ↓
clinical.episode span
       ↓
episode registry
       ↓
child activities/events
       ↓
explicit episode close
```

---

### B. Correct episode initiation model

We need to remove the conceptual legacy:

```text
ALARM → EPISODE
```

and ensure:

```text
EPISODE JOURNAL
        ↓
EPISODE
```

is the canonical mechanism.

The existing DB enum should eventually be migrated.

---

### C. Finish alarm service

`alarm_service.py` exists, but the complete alarm lifecycle is still to be implemented.

Desired model:

```text
Grafana
   │
   │ alert generated from InfluxDB
   ▼
Middleware webhook
   │
   ▼
AlarmService
   │
   ├── create alarm
   ├── trigger event
   ├── associate encounter
   ├── associate episode if one exists
   │
   ├── respond
   ├── dismiss
   └── unanswered
```

---

# 21. Grafana → Middleware alarm integration

This is still future implementation.

The final flow should be:

```text
InfluxDB
   │
   │ vitals
   ▼
Grafana
   │
   │ alert rule
   ▼
Alarm
   │
   │ webhook
   ▼
Clinical Middleware
   │
   ├── PostgreSQL
   │
   └── Tempo
```

There is **no IncidentRelay** in this architecture.

---

# 22. Episode + alarm interaction

Suppose:

```text
08:00 Encounter begins

08:05 Staff creates EPISODE
      ↓
      Episode EPI-001 opens

08:10 SpO₂ falls
      ↓
      InfluxDB
      ↓
      Grafana alert
      ↓
      Alarm A-001

08:12 Nurse responds

08:20 Episode closes

16:30 Encounter closes
```

Trace:

```text
clinical.encounter
│
└── clinical.episode
     │
     ├── event: clinical.alarm.triggered
     ├── event: clinical.alarm.responded
     └── journal activity spans
```

That is the intended clinical observability structure.

---

# 23. Complete root directory structure

Based on the project structure we have established, the current root should be understood as:

```text
Healthcare/
│
├── DB-foundation-01/
│   │
│   ├── compose.yaml
│   │
│   ├── db/
│   │   │
│   │   ├── influxdb/
│   │   │   └── vital-contract.txt
│   │   │
│   │   └── postgres/
│   │       └── init/
│   │           ├── 01-schema.sql
│   │           ├── 02-seed.sql
│   │           └── [Phase-03 migration SQL]
│   │
│   └── phase-01.md
│
│
├── Dashboard-00/
│   │
│   ├── compose.yaml
│   │
│   ├── grafana/
│   │   │
│   │   ├── dashboards/
│   │   │
│   │   └── provisioning/
│   │       └── datasources/
│   │           └── datasources.yml
│   │
│   └── phase-00.md
│
│
├── Traces-02/
│   │
│   ├── compose.yaml
│   │
│   ├── otel/
│   │   └── otel-collector.yml
│   │
│   ├── tempo/
│   │   └── tempo.yml
│   │
│   └── phase-02.md
│
│
├── Middle-ware-03/
│   │
│   ├── app/
│   │   │
│   │   ├── services/
│   │   │   ├── alarm_service.py
│   │   │   ├── encounter_service.py
│   │   │   ├── episode_service.py
│   │   │   ├── journal_service.py
│   │   │   └── trace_service.py
│   │   │
│   │   └── tracing/
│   │       ├── context.py
│   │       ├── exporter.py
│   │       ├── provider.py
│   │       └── registry.py
│   │
│   └── [tests / integration scripts added during development]
│
│
├── requirements.txt
│
└── Readme.md
```

The exact filenames of additional migration/test files may grow as Phase 03 is finalized, but this is the **architectural root structure** we have been working from.

---

# 24. Current complete architecture

Putting everything together:

```text
                              ┌──────────────────┐
                              │      Patient     │
                              └────────┬─────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
              Patient record                         Vital devices
                    │                                     │
                    ▼                                     ▼
               PostgreSQL                               InfluxDB
                    │                                     │
                    │                                     ▼
                    │                                  Grafana
                    │                                     │
                    │                               Alert condition
                    │                                     │
                    │                                     ▼
                    │                                   ALARM
                    │                                     │
                    │                              webhook to middleware
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                              Clinical Middleware
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
                ▼                      ▼                      ▼
             Journals              Episodes                Alarms
                │                      │                      │
                │                      │                      │
                └──────────────────────┼──────────────────────┘
                                       │
                                       ▼
                              OpenTelemetry SDK
                                       │
                                       ▼
                              OTel Collector
                                       │
                                       ▼
                                     Tempo
                                       │
                                       ▼
                                    Grafana
```

---

# 25. What Phase 03 should ultimately produce

The finished middleware should support this complete lifecycle:

```text
CREATE PATIENT
      │
      ▼
START ENCOUNTER
      │
      ├── root trace span
      │
      ├── EVENT journal
      │
      ├── FIXED_ACTIVITY journal
      │
      ├── ONGOING_ACTIVITY journal
      │        │
      │        └── explicit close
      │
      ├── EPISODE journal
      │        │
      │        ▼
      │      EPISODE span
      │        │
      │        ├── activities
      │        ├── events
      │        └── alarms
      │
      ├── Grafana alarm
      │        │
      │        ├── triggered
      │        ├── responded
      │        ├── dismissed
      │        └── unanswered
      │
      ▼
CLOSE EPISODE
      │
      ▼
CLOSE ENCOUNTER
      │
      ▼
TRACE COMPLETE
```

---

# 26. Phase 03 definition of done

I would consider Phase 03 complete when one automated integration test can perform:

```text
1. Create/find patient
2. Start encounter
3. Verify root span
4. Persist trace_id/span_id
5. Create EVENT journal
6. Create FIXED_ACTIVITY journal
7. Open ONGOING_ACTIVITY
8. Verify it remains open
9. Create EPISODE journal
10. Create episode span
11. Create activity inside episode
12. Create activity outside episode
13. Generate/ingest Grafana alarm
14. Attach alarm to encounter/episode
15. Record alarm response
16. Close ongoing activity
17. Close episode
18. Close encounter
19. Verify PostgreSQL state
20. Verify trace hierarchy in Tempo/Grafana
21. Verify all registries are cleaned
```

The final trace should visibly demonstrate:

```text
clinical.encounter
│
├── journal activity
│
├── clinical.episode
│   ├── journal activity
│   ├── journal activity
│   ├── alarm.triggered
│   └── alarm.responded
│
└── journal activity
```

That will give us a genuinely meaningful **clinical trace**, rather than merely proving that OpenTelemetry can export spans.

---

# 27. Where we are right now

The project is currently at:

```text
Phase 00  ████████████████████  DONE
Grafana

Phase 01  ████████████████████  DONE
PostgreSQL + InfluxDB

Phase 02  ████████████████████  DONE
Tempo + OTel Collector + basic tracing

Phase 03  ████████████░░░░░░░░  IN PROGRESS
Clinical Middleware
```

More specifically, **we have already proven the hardest basic tracing plumbing**:

```text
PostgreSQL
    ↕
Middleware
    ↓
OpenTelemetry
    ↓
Collector
    ↓
Tempo
    ↓
Grafana
```

and we have already proven:

```text
Encounter root
       ↓
Journal child
       ↓
Open/close lifecycle
       ↓
Registry lifecycle
```

The next logical implementation step is therefore **not more infrastructure**.

It is:

> **Finish `EpisodeService` + episode tracing and test the complete encounter → episode → journal hierarchy.**

After that:

```text
Episode tracing
      ↓
AlarmService
      ↓
Grafana → Middleware webhook
      ↓
Alarm lifecycle
      ↓
Full end-to-end Phase 03 test
```

That keeps the implementation aligned with the model we've now settled on and avoids reintroducing the discarded IncidentRelay architecture.

[1]: https://grafana.com/docs/tempo/latest/?utm_source=chatgpt.com "Grafana Tempo | Grafana Tempo documentation"
[2]: https://opentelemetry.io/docs/specs/otel/trace/api/?utm_source=chatgpt.com "Tracing API | OpenTelemetry"
[3]: https://grafana.com/docs/tempo/latest/set-up-for-tracing/instrument-send/set-up-collector/otel-collector/?utm_source=chatgpt.com "OpenTelemetry Collector | Grafana Tempo documentation"
