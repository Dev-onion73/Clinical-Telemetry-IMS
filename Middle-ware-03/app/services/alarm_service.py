
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.services.trace_service import TraceService


class AlarmService:

    def __init__(self, trace_service=None):
        self.trace_service = trace_service or TraceService()

    # ============================================================
    # GRAFANA WEBHOOK
    # ============================================================

    def process_grafana_payload(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        alerts = payload.get("alerts", [])

        if not isinstance(alerts, list):
            raise ValueError(
                "Grafana payload 'alerts' must be a list"
            )

        processed = 0
        started = 0
        resolved = 0
        ignored = 0

        errors: list[dict[str, Any]] = []

        for index, alert in enumerate(alerts):

            try:

                result = self.process_grafana_alert(
                    alert
                )

                processed += 1

                if result == "started":
                    started += 1

                elif result == "resolved":
                    resolved += 1

                elif result == "ignored":
                    ignored += 1

            except Exception as exc:

                errors.append(
                    {
                        "index": index,
                        "error": str(exc),
                    }
                )

                print(
                    "\n!!!!!!!!!!!!!!!! ALERT PROCESSING ERROR !!!!!!!!!!!!!!!!"
                )
                print(
                    f"  alert index : {index}"
                )
                print(
                    f"  error       : {exc}"
                )
                print(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                )

        result = {
            "processed": processed,
            "started": started,
            "resolved": resolved,
            "ignored": ignored,
            "errors": errors,
        }

        print(
            "\n================ GRAFANA TRACE RESULT ================"
        )
        print(
            f"  processed : {processed}"
        )
        print(
            f"  started   : {started}"
        )
        print(
            f"  resolved  : {resolved}"
        )
        print(
            f"  ignored   : {ignored}"
        )
        print(
            f"  errors    : {errors}"
        )
        print(
            "=======================================================\n"
        )

        return result

    # ============================================================
    # INDIVIDUAL GRAFANA ALERT
    # ============================================================

    def process_grafana_alert(
        self,
        alert: dict[str, Any],
    ) -> str:

        if not isinstance(alert, dict):
            raise ValueError(
                "Grafana alert must be an object"
            )

        labels = alert.get("labels") or {}

        if not isinstance(labels, dict):
            raise ValueError(
                "Grafana alert labels must be an object"
            )

        alert_name = labels.get(
            "alertname"
        )

        # Grafana infrastructure alert.
        # Do not put this into the clinical trace.
        if alert_name == "DatasourceNoData":
            return "ignored"

        status = str(
            alert.get("status", "")
        ).lower()

        if status not in {
            "firing",
            "resolved",
        }:
            return "ignored"

        fingerprint = alert.get(
            "fingerprint"
        )

        if not fingerprint:
            raise ValueError(
                "Clinical Grafana alert is missing fingerprint"
            )

        fingerprint = str(
            fingerprint
        )

        encounter_id = labels.get(
            "encounter_id"
        )

        if not encounter_id:
            raise ValueError(
                f"Clinical Grafana alert "
                f"'{fingerprint}' is missing "
                "required label: encounter_id"
            )

        encounter_id = str(
            encounter_id
        )

        patient_id = labels.get(
            "patient_id"
        )

        if patient_id is not None:
            patient_id = str(
                patient_id
            )

        rule_name = (
            labels.get("rulename")
            or labels.get("alertname")
            or "clinical_alert"
        )

        rule_name = str(
            rule_name
        )

        starts_at = self._parse_grafana_timestamp(
            alert.get("startsAt"),
            field_name="startsAt",
        )

        attributes = self._build_alert_attributes(
            alert=alert,
            labels=labels,
        )

        # ========================================================
        # FIRING
        # ========================================================

        if status == "firing":

            threshold_span = (
                self.trace_service.start_alert(
                    fingerprint=fingerprint,
                    alert_name=rule_name,
                    starts_at=starts_at,
                    encounter_id=encounter_id,
                    patient_id=patient_id,
                    attributes=attributes,
                )
            )

            trace_id, span_id = (
                self._span_ids(
                    threshold_span
                )
            )

            print(
                "\n[ALARM SERVICE] FIRING PROCESSED"
            )
            print(
                f"  fingerprint : {fingerprint}"
            )
            print(
                f"  trace_id    : {trace_id}"
            )
            print(
                f"  span_id     : {span_id}"
            )

            return "started"

        # ========================================================
        # RESOLVED
        # ========================================================

        ends_at = self._parse_grafana_timestamp(
            alert.get("endsAt"),
            field_name="endsAt",
        )

        threshold_span = (
            self.trace_service.end_alert(
                fingerprint=fingerprint,
                starts_at=starts_at,
                ends_at=ends_at,
                alert_name=rule_name,
                encounter_id=encounter_id,
                patient_id=patient_id,
                attributes=attributes,
            )
        )

        trace_id, span_id = (
            self._span_ids(
                threshold_span
            )
        )

        print(
            "\n[ALARM SERVICE] RESOLUTION PROCESSED"
        )
        print(
            f"  fingerprint : {fingerprint}"
        )
        print(
            f"  trace_id    : {trace_id}"
        )
        print(
            f"  threshold   : {span_id}"
        )

        return "resolved"

    # ============================================================
    # TIMESTAMP PARSING
    # ============================================================

    @staticmethod
    def _parse_grafana_timestamp(
        value: Any,
        field_name: str,
    ) -> datetime:

        if not isinstance(
            value,
            str,
        ) or not value:

            raise ValueError(
                f"Clinical Grafana alert "
                f"is missing valid {field_name}"
            )

        # Grafana's unresolved sentinel.
        if value == (
            "0001-01-01T00:00:00Z"
        ):

            raise ValueError(
                f"Grafana {field_name} "
                "contains unresolved default timestamp"
            )

        normalized = value

        if normalized.endswith("Z"):
            normalized = (
                normalized[:-1]
                + "+00:00"
            )

        try:

            parsed = datetime.fromisoformat(
                normalized
            )

        except ValueError as exc:

            raise ValueError(
                f"Invalid Grafana "
                f"{field_name}: {value}"
            ) from exc

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    # ============================================================
    # SPAN IDS
    # ============================================================

    @staticmethod
    def _span_ids(
        span,
    ) -> tuple[str, str]:

        context = (
            span.get_span_context()
        )

        return (
            format(
                context.trace_id,
                "032x",
            ),
            format(
                context.span_id,
                "016x",
            ),
        )

    # ============================================================
    # JSON SERIALIZATION
    # ============================================================

    @staticmethod
    def _json_string(
        value: Any,
    ) -> str:

        try:

            return json.dumps(
                value,
                default=str,
                sort_keys=True,
            )

        except (
            TypeError,
            ValueError,
        ):

            return str(value)

    # ============================================================
    # ALERT ATTRIBUTES
    # ============================================================

    @classmethod
    def _build_alert_attributes(
        cls,
        alert: dict[str, Any],
        labels: dict[str, Any],
    ) -> dict[str, str]:

        attributes: dict[str, str] = {}

        # --------------------------------------------------------
        # Grafana identity
        # --------------------------------------------------------

        if alert.get("fingerprint"):

            attributes[
                "clinical.alert.fingerprint"
            ] = str(
                alert["fingerprint"]
            )

        if labels.get("alertname"):

            attributes[
                "clinical.alert.name"
            ] = str(
                labels["alertname"]
            )

        if labels.get("rulename"):

            attributes[
                "clinical.alert.rule_name"
            ] = str(
                labels["rulename"]
            )

        # ruleUID is supplied at alert level
        if alert.get("ruleUID"):

            attributes[
                "clinical.alert.rule_uid"
            ] = str(
                alert["ruleUID"]
            )

        # --------------------------------------------------------
        # Clinical identity
        # --------------------------------------------------------

        if labels.get("patient_id"):

            attributes[
                "clinical.patient.id"
            ] = str(
                labels["patient_id"]
            )

        if labels.get("encounter_id"):

            attributes[
                "clinical.encounter.id"
            ] = str(
                labels["encounter_id"]
            )

        if labels.get("device_id"):

            attributes[
                "clinical.alert.device_id"
            ] = str(
                labels["device_id"]
            )

        # --------------------------------------------------------
        # Grafana metadata
        # --------------------------------------------------------

        if labels.get("datasource_uid"):

            attributes[
                "grafana.datasource_uid"
            ] = str(
                labels["datasource_uid"]
            )

        if labels.get("grafana_folder"):

            attributes[
                "grafana.folder"
            ] = str(
                labels["grafana_folder"]
            )

        if labels.get("ref_id"):

            attributes[
                "grafana.ref_id"
            ] = str(
                labels["ref_id"]
            )

        if alert.get("generatorURL"):

            attributes[
                "grafana.generator_url"
            ] = str(
                alert["generatorURL"]
            )

        if alert.get("silenceURL"):

            attributes[
                "grafana.silence_url"
            ] = str(
                alert["silenceURL"]
            )

        if alert.get("dashboardURL"):

            attributes[
                "grafana.dashboard_url"
            ] = str(
                alert["dashboardURL"]
            )

        if alert.get("panelURL"):

            attributes[
                "grafana.panel_url"
            ] = str(
                alert["panelURL"]
            )

        # --------------------------------------------------------
        # Alert evaluation data
        # --------------------------------------------------------

        if alert.get("values") is not None:

            attributes[
                "clinical.alert.values"
            ] = cls._json_string(
                alert["values"]
            )

        if alert.get("valueString") is not None:

            attributes[
                "clinical.alert.value_string"
            ] = str(
                alert["valueString"]
            )

        if alert.get("annotations") is not None:

            attributes[
                "clinical.alert.annotations"
            ] = cls._json_string(
                alert["annotations"]
            )

        return attributes


alarm_service = AlarmService()
