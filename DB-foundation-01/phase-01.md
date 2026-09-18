# Healthcare Incident Management

## Phase 01 — Clinical Data Foundation

**Status:** Completed

### Objective

Phase 01 establishes the initial authoritative data stores for the Healthcare Incident Management system.

The phase contains only:

```text
PostgreSQL
InfluxDB
```

Grafana has been moved to Phase 00 and is therefore no longer part of the Phase 01 Compose deployment.

---

## 1. PostgreSQL

PostgreSQL is the authoritative store for structured clinical records.

The implemented schema contains:

```text
patients
encounters
episodes
journals
```

### Patients

Stores patient identity and demographic information.

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

### Encounters

Represents a complete interaction/admission involving a patient.

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

Encounter lifecycle:

```text
OPEN → ACTIVE → CLOSED
```

A new admission or readmission creates a new encounter.

### Episodes

Represents a clinically meaningful interval within an encounter.

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

The current implementation reserves:

```text
trace_id
```

for future Tempo integration.

Likewise:

```text
source_paging_incident_id
```

is reserved for future IncidentRelay integration.

Episode lifecycle:

```text
OPEN → ACTIVE → CLOSED
```

### Journals

Stores independent clinical documentation.

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

Journals are intentionally **not attached to episodes**.

They remain independent clinical records associated with the patient and encounter.

---

## 2. Important Data Ownership Decisions

### No PostgreSQL `events` table

A separate relational event table was deliberately removed.

Future trace events will be represented as OpenTelemetry span events in Tempo.

### No vitals in PostgreSQL

Continuous physiological measurements are stored in InfluxDB rather than duplicated into PostgreSQL.

### No journals inside episodes

Episodes represent intervals. Journals remain independent clinical documentation.

### No paging data in PostgreSQL

Operational paging data will belong to IncidentRelay when that subsystem is introduced.

---

## 3. InfluxDB

InfluxDB is the authoritative store for continuous patient vitals.

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

Every measurement uses its own timestamp.

The architecture therefore keeps:

```text
PostgreSQL
    ↓
Clinical records

InfluxDB
    ↓
Continuous vitals
```

as separate data domains.

---

## 4. Seed Data

The implemented seed dataset contains:

```text
3 patients
4 encounters
4 episodes
5 journals
```

The dataset includes representative:

* emergency care
* outpatient follow-up
* routine outpatient care
* inpatient procedure
* clinical journal documentation
* alarm-initiated episode
* scheduled-procedure episode
* manual episode

The emergency example includes a medication-related allergic reaction scenario to provide meaningful clinical data for later tracing and incident-management phases.

---

## 5. Docker Deployment

Phase 01 has its own Compose project.

Current Phase 01 services:

```text
clinical-postgres
clinical-influxdb
```

Grafana is intentionally excluded because it is owned by Phase 00.

### PostgreSQL

```text
Image: postgres:17
Port: 5432
Database: clinical
```

Persistent volume:

```text
postgres-data
```

Initialization:

```text
db/postgres/init/
├── 01-schema.sql
└── 02-seed.sql
```

### InfluxDB

```text
Image: influxdb:2.7
Port: 8086
Organization: clinical
Bucket: vitals
```

Persistent volume:

```text
influx-data
```

---

## 6. Shared Network

Phase 01 services join:

```text
clinical-net
```

This is an external shared Docker network used by Phase 00 and future phases.

The current relationship is:

```text
                  clinical-net
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
 clinical-postgres clinical-influxdb clinical-grafana
    Phase 01           Phase 01          Phase 00
```

This allows Grafana to access the Phase 01 services without being part of the Phase 01 Compose file.

---

## 7. Validation

Phase 01 was successfully deployed and validated.

Completed:

* PostgreSQL container healthy.
* InfluxDB container healthy.
* PostgreSQL schema initialized.
* PostgreSQL seed script configured.
* InfluxDB initialized.
* PostgreSQL datasource successfully connected through Grafana.
* InfluxDB datasource successfully connected through Grafana.
* Persistent volumes configured.
* Shared `clinical-net` configured.
* Grafana successfully communicates with both Phase 01 data stores.

---

## 8. Explicitly Deferred

The following are **not part of Phase 01**:

```text
Tempo
OpenTelemetry Collector
IncidentRelay
Clinical Backend
Clinical Frontend
Consumer
Kafka
```

These belong to later phases.

---

## Phase 01 Result

Phase 01 successfully establishes the **clinical data foundation**:

```text
             Phase 01
        ┌─────────────────┐
        │                 │
        │   PostgreSQL    │
        │ Clinical Data   │
        │                 │
        ├─────────────────┤
        │                 │
        │    InfluxDB     │
        │ Continuous      │
        │ Vitals          │
        │                 │
        └────────┬────────┘
                 │
            clinical-net
                 │
                 ▼
        Phase 00 — Grafana
```

The storage layer is now ready for Phase 02, where the **tracing foundation (OpenTelemetry + Tempo)** can be introduced without redesigning Phase 00 or Phase 01.
