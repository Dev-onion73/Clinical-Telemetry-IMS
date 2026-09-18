# Healthcare Incident Management

## Phase 00 — Visualization Foundation

**Status:** Completed

### Objective

Phase 00 establishes Grafana as the **persistent, project-wide visualization and correlation layer** for the Healthcare Incident Management system.

Grafana is intentionally separated from the individual implementation phases so that future phases can extend its configuration without deploying additional Grafana instances.

### Components

* Grafana
* Persistent Grafana storage
* Grafana datasource provisioning
* Grafana dashboard provisioning
* Shared `clinical-net` Docker network

### Grafana Role

Grafana is responsible for visualizing and correlating data from the independent system components.

It does **not** own clinical, vitals, trace, or incident data.

The intended architecture is:

```text
PostgreSQL ───────┐
                  │
InfluxDB ─────────┼──► Grafana
                  │
Tempo ────────────┤
                  │
IncidentRelay ────┘
```

Only the components that exist in a particular phase are connected to Grafana at that point.

### Current Datasources

At the completion of Phase 00 + Phase 01, Grafana has:

```text
Clinical PostgreSQL
Clinical InfluxDB
```

Both datasource connections have been successfully tested.

Tempo will be added during Phase 02 without creating another Grafana instance.

### Persistence

Grafana uses its own persistent Docker volume:

```text
grafana-data
```

The Grafana container remains independent from the Phase 01 database containers.

### Shared Network

Grafana is connected to:

```text
clinical-net
```

This is an external shared Docker network used by the different phase deployments.

This allows services from future phases to become accessible to the existing Grafana instance without recreating Grafana.

### Configuration Evolution

Grafana configuration is designed to grow cumulatively:

```text
Phase 00
    Grafana

Phase 01
    + PostgreSQL datasource
    + InfluxDB datasource

Phase 02
    + Tempo datasource

Future phases
    + additional datasources
    + additional dashboards
```

The Grafana container, port, and persistent volume remain stable throughout the project.

### Completed Validation

* Grafana deployed successfully.
* Grafana UI accessible on port `3000`.
* Grafana persistent storage configured.
* PostgreSQL datasource provisioned successfully.
* InfluxDB datasource provisioned successfully.
* Both datasource connections tested successfully.
* Grafana healthcheck configured and passing.
* Grafana connected to the shared `clinical-net`.

### Phase 00 Result

Phase 00 successfully establishes **Grafana as the permanent visualization and correlation layer** of the system.

It will be extended throughout subsequent phases rather than recreated.
