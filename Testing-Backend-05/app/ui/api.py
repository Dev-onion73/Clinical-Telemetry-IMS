from __future__ import annotations

from typing import Any

import requests


class TestingBackendAPI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Generic request
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            timeout=10,
            **kwargs,
        )

        response.raise_for_status()

        if not response.content:
            return None

        return response.json()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self):
        return self._request(
            "GET",
            "/health",
        )

    # ------------------------------------------------------------------
    # Stable vitals
    # ------------------------------------------------------------------

    def start_stable_vitals(
        self,
        *,
        patient_id: str,
        encounter_id: str,
        device_id: str,
        start_time: str,
        metrics: dict[str, float],
        interval_seconds: float,
    ):
        return self._request(
            "POST",
            "/testing/vitals/stable/start",
            json={
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "device_id": device_id,
                "start_time": start_time,
                "metrics": metrics,
                "interval_seconds": interval_seconds,
            },
        )

    def stop_stable_vitals(
        self,
        source_id: str,
    ):
        return self._request(
            "POST",
            f"/testing/vitals/stable/{source_id}/stop",
        )

    def get_stable_vitals(self):
        return self._request(
            "GET",
            "/testing/vitals/stable",
        )

    def get_stable_vital_source(
        self,
        source_id: str,
    ):
        return self._request(
            "GET",
            f"/testing/vitals/stable/{source_id}",
        )

    # ------------------------------------------------------------------
    # Alert catalog
    # ------------------------------------------------------------------

    def get_alert_catalog(self):
        return self._request(
            "GET",
            "/testing/alerts/catalog",
        )

    # ------------------------------------------------------------------
    # One-shot alert
    #
    # These are instantaneous.
    #
    # actual_timestamp is deliberately NOT sent.
    # ------------------------------------------------------------------

    def inject_alert(
        self,
        *,
        scenario: str,
        patient_id: str,
        encounter_id: str,
        device_id: str,
        spoof_timestamp: str | None = None,
    ):
        payload = {
            "scenario": scenario,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "device_id": device_id,
            "spoof_timestamp": spoof_timestamp,
        }

        return self._request(
            "POST",
            "/testing/alerts/inject",
            json=payload,
        )

    # ------------------------------------------------------------------
    # Continuous threshold alerts
    # ------------------------------------------------------------------

    def start_threshold(
        self,
        *,
        scenario: str,
        patient_id: str,
        encounter_id: str,
        device_id: str,
        start_time: str,
        interval_seconds: float,
        spoof_timestamp: str | None = None,
    ):
        payload = {
            "scenario": scenario,
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "device_id": device_id,
            "start_time": start_time,
            "interval_seconds": interval_seconds,
            "spoof_timestamp": spoof_timestamp,
        }

        return self._request(
            "POST",
            "/testing/alerts/threshold/start",
            json=payload,
        )

    def stop_threshold(
        self,
        source_id: str,
    ):
        return self._request(
            "POST",
            f"/testing/alerts/threshold/{source_id}/stop",
        )

    def get_threshold_sources(self):
        return self._request(
            "GET",
            "/testing/alerts/threshold",
        )

    def get_threshold_source(
        self,
        source_id: str,
    ):
        return self._request(
            "GET",
            f"/testing/alerts/threshold/{source_id}",
        )