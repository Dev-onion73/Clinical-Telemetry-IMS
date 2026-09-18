## Phase 02 — Tracing Foundation

**Status: Completed and verified**

Phase 02 established the tracing infrastructure for the Healthcare Incident Management system. It is responsible only for **OpenTelemetry ingestion and Tempo trace storage**.

### Implemented

* **Grafana Tempo 3.0.0**

  * Persistent trace storage using a Docker volume.
  * OTLP gRPC receiver on `4317`.
  * OTLP HTTP receiver on `4318`.
  * Tempo query API exposed on `3200`.
  * Corrected receiver binding to `0.0.0.0` so the separate OTel Collector can connect.

* **OpenTelemetry Collector**

  * OTLP gRPC receiver.
  * OTLP HTTP receiver.
  * Batch processor.
  * OTLP gRPC exporter to `clinical-tempo:4317`.
  * Corrected receiver binding to `0.0.0.0`.
  * Collector version currently resolves to `0.161.0`.

* **Synthetic trace producer**

  * Python OpenTelemetry SDK.
  * Generates an Encounter → Episode trace hierarchy.
  * Adds clinical identifiers as span attributes.
  * Generates a journal-related span event.
  * Sends traces through the Collector rather than directly to Tempo.

### Verified end-to-end path

```text
Synthetic Producer
       │
       │ OTLP
       ▼
OTel Collector
       │
       │ OTLP gRPC
       ▼
Tempo
       │
       │ HTTP Query API
       ▼
Trace retrieved successfully
```

The successfully retrieved test trace contained:

```text
TEST_ENCOUNTER
└── TEST_EPISODE
    └── TEST_JOURNAL_ENTRY
```

with:

* `clinical.patient_id = PAT-0001`
* `clinical.encounter_id = E1`
* `clinical.episode_id = E1_EP1`
* journal source reference:

  * `source_type = journal`
  * `source_id = JRN-0002`

Parent/child span relationships, span attributes, and span events were all verified.

### Grafana integration

Tempo was added as the **Clinical Tempo** datasource to the existing Phase 00 Grafana instance.

Grafana now has:

```text
Clinical PostgreSQL
Clinical InfluxDB
Clinical Tempo
```

The Tempo datasource was tested successfully.

### Architectural decisions established

* **Tempo owns temporal trace representation**, not clinical source-of-truth data.
* PostgreSQL remains authoritative for journals, encounters, episodes, etc.
* InfluxDB remains authoritative for continuous vitals.
* Vitals **do not flow through OTel/Tempo**.
* Journals remain in PostgreSQL; their occurrence can be represented in Tempo through span events or clinical spans.
* An Encounter maps conceptually to a root trace/span.
* An Episode maps to a child span.
* Clinical activity belonging to an Episode is represented underneath that Episode.
* `episodes.trace_id` is reserved for the corresponding Tempo trace.
* Trace attributes can retain references such as `source_type` and `source_id` without duplicating the underlying clinical record.

### Phase 02 deployment boundary

Phase 02 contains only:

```text
phase-02-tracing/
├── docker-compose.yml
├── tempo/
│   └── tempo.yml
├── otel/
│   └── otel-collector.yml
├── tests/
│   ├── requirements.txt
│   └── synthetic-traces.py
└── README.md
```

It **does not contain Grafana, PostgreSQL, or InfluxDB**. Those remain owned by Phases 00 and 01 respectively.

### Final Phase 02 state

```text
✓ Tempo deployed
✓ OTel Collector deployed
✓ OTLP ingestion verified
✓ Collector → Tempo export verified
✓ Tempo trace storage verified
✓ Tempo query API verified
✓ Parent/child spans verified
✓ Span attributes verified
✓ Span events verified
✓ Clinical source references verified
✓ Grafana → Tempo integration verified
✓ Shared clinical-net verified
```

**Phase 02 is therefore complete.** The next infrastructure component is **Phase 03 — IncidentRelay**, after which the infrastructure layer will be in place for the Clinical Backend.
