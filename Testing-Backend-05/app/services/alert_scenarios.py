from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.config import settings
from app.messaging.kafka import KafkaProducer
from app.schemas.alerts import (
    AlertScenarioSource,
    ScenarioType,
)
from app.schemas.vitals import VitalReading


class AlertScenarioService:
    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    BASELINE = {
        "spo2": 98.0,
        "heart_rate": 80.0,
        "temperature": 37.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
    }

    # ------------------------------------------------------------------
    # Scenario catalog
    # ------------------------------------------------------------------

    SEED_SCENARIOS = [
        "spo2_drop",
        "hr_drop",
        "hr_rise",
        "temperature_drop",
        "temperature_rise",
        "respiratory_rate_drop",
        "respiratory_rate_rise",
        "systolic_bp_drop",
        "systolic_bp_rise",
        "diastolic_bp_drop",
        "diastolic_bp_rise",
    ]

    THRESHOLD_SCENARIOS = [
        "spo2_medium_low",
        "spo2_high_low",

        "hr_medium_low",
        "hr_high_low",
        "hr_medium_high",
        "hr_high_high",

        "temperature_medium_low",
        "temperature_high_low",
        "temperature_medium_high",
        "temperature_high_high",

        "respiratory_rate_medium_low",
        "respiratory_rate_high_low",
        "respiratory_rate_medium_high",
        "respiratory_rate_high_high",

        "systolic_bp_medium_low",
        "systolic_bp_high_low",
        "systolic_bp_medium_high",
        "systolic_bp_high_high",

        "diastolic_bp_medium_low",
        "diastolic_bp_high_low",
        "diastolic_bp_medium_high",
        "diastolic_bp_high_high",
    ]

    TREND_SCENARIOS = [
        "spo2_down",
        "hr_down",
        "hr_up",
        "temperature_down",
        "temperature_up",
        "respiratory_rate_down",
        "respiratory_rate_up",
        "systolic_bp_down",
        "systolic_bp_up",
        "diastolic_bp_down",
        "diastolic_bp_up",
    ]

    ALL_SCENARIOS = (
        SEED_SCENARIOS
        + THRESHOLD_SCENARIOS
        + TREND_SCENARIOS
    )

    # ------------------------------------------------------------------
    # Threshold values
    # ------------------------------------------------------------------

    THRESHOLD_VALUES = {
        "spo2_medium_low": ("spo2", 94.0),
        "spo2_high_low": ("spo2", 91.0),

        "hr_medium_low": ("heart_rate", 45.0),
        "hr_high_low": ("heart_rate", 35.0),
        "hr_medium_high": ("heart_rate", 110.0),
        "hr_high_high": ("heart_rate", 130.0),

        "temperature_medium_low": ("temperature", 35.5),
        "temperature_high_low": ("temperature", 34.5),
        "temperature_medium_high": ("temperature", 38.2),
        "temperature_high_high": ("temperature", 39.0),

        "respiratory_rate_medium_low": (
            "respiratory_rate",
            10.0,
        ),
        "respiratory_rate_high_low": (
            "respiratory_rate",
            7.0,
        ),
        "respiratory_rate_medium_high": (
            "respiratory_rate",
            22.0,
        ),
        "respiratory_rate_high_high": (
            "respiratory_rate",
            28.0,
        ),

        "systolic_bp_medium_low": (
            "systolic_bp",
            95.0,
        ),
        "systolic_bp_high_low": (
            "systolic_bp",
            85.0,
        ),
        "systolic_bp_medium_high": (
            "systolic_bp",
            170.0,
        ),
        "systolic_bp_high_high": (
            "systolic_bp",
            190.0,
        ),

        "diastolic_bp_medium_low": (
            "diastolic_bp",
            55.0,
        ),
        "diastolic_bp_high_low": (
            "diastolic_bp",
            45.0,
        ),
        "diastolic_bp_medium_high": (
            "diastolic_bp",
            105.0,
        ),
        "diastolic_bp_high_high": (
            "diastolic_bp",
            115.0,
        ),
    }

    # ------------------------------------------------------------------
    # Trend targets
    # ------------------------------------------------------------------

    TREND_TARGETS = {
        "spo2_down": ("spo2", 90.0),
        "hr_down": ("heart_rate", 40.0),
        "hr_up": ("heart_rate", 130.0),
        "temperature_down": ("temperature", 35.0),
        "temperature_up": ("temperature", 39.0),
        "respiratory_rate_down": (
            "respiratory_rate",
            8.0,
        ),
        "respiratory_rate_up": (
            "respiratory_rate",
            28.0,
        ),
        "systolic_bp_down": (
            "systolic_bp",
            85.0,
        ),
        "systolic_bp_up": (
            "systolic_bp",
            190.0,
        ),
        "diastolic_bp_down": (
            "diastolic_bp",
            45.0,
        ),
        "diastolic_bp_up": (
            "diastolic_bp",
            115.0,
        ),
    }

    def __init__(
        self,
        kafka_producer: KafkaProducer,
    ):
        self._kafka_producer = kafka_producer

        self._sources: dict[
            str,
            AlertScenarioSource,
        ] = {}

        self._tasks: dict[
            str,
            asyncio.Task,
        ] = {}

    # ==================================================================
    # Catalog
    # ==================================================================

    @classmethod
    def catalog(cls) -> dict[str, list[str]]:
        return {
            "seed": list(cls.SEED_SCENARIOS),
            "threshold": list(
                cls.THRESHOLD_SCENARIOS
            ),
            "trend": list(cls.TREND_SCENARIOS),
        }

    @classmethod
    def scenario_type(
        cls,
        scenario: str,
    ) -> ScenarioType:
        if scenario in cls.SEED_SCENARIOS:
            return ScenarioType.SEED

        if scenario in cls.THRESHOLD_SCENARIOS:
            return ScenarioType.THRESHOLD

        if scenario in cls.TREND_SCENARIOS:
            return ScenarioType.TREND

        raise ValueError(
            f"Unknown alert scenario: {scenario}"
        )

    # ==================================================================
    # Start
    # ==================================================================

    async def start_threshold(
        self,
        *,
        patient_id: str,
        encounter_id: str,
        device_id: str,
        scenario: str,
        start_time: datetime,
        interval_seconds: float,
        spoof_timestamp: datetime | None = None,
    ) -> AlertScenarioSource:

        scenario = scenario.strip().lower()

        if scenario not in self.THRESHOLD_SCENARIOS:
            raise ValueError(
                f"Scenario '{scenario}' is not a threshold scenario."
            )

        existing = self.get_running_for_scenario(
            scenario
        )

        if existing is not None:
            raise ValueError(
                f"Threshold scenario '{scenario}' "
                f"is already running as "
                f"{existing.source_id}."
            )

        source_id = (
            f"THR-{uuid4().hex[:8].upper()}"
        )

        if spoof_timestamp is None:
            spoof_timestamp = start_time

        source = AlertScenarioSource(
            source_id=source_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            device_id=device_id,
            status="RUNNING",
            started_at=start_time,
            scenario=scenario,
            scenario_type=ScenarioType.THRESHOLD,
            interval_seconds=interval_seconds,
            spoof_timestamp=spoof_timestamp,
            sample_index=0,
            last_reading=None,
        )

        self._sources[source_id] = source

        task = asyncio.create_task(
            self._run_source(source_id)
        )

        self._tasks[source_id] = task

        return source

    # ==================================================================
    # Stop
    # ==================================================================

    async def stop_source(
        self,
        source_id: str,
    ) -> AlertScenarioSource | None:

        source = self._sources.get(
            source_id
        )

        if source is None:
            return None

        task = self._tasks.pop(
            source_id,
            None,
        )

        if task is not None:
            task.cancel()

            try:
                await task

            except asyncio.CancelledError:
                pass

        stopped = source.model_copy(
            update={
                "status": "STOPPED",
            }
        )

        self._sources[
            source_id
        ] = stopped

        return stopped

    # ==================================================================
    # Queries
    # ==================================================================

    def list_sources(
        self,
    ) -> list[AlertScenarioSource]:

        return list(
            self._sources.values()
        )

    def get_source(
        self,
        source_id: str,
    ) -> AlertScenarioSource | None:

        return self._sources.get(
            source_id
        )

    def get_running_for_scenario(
        self,
        scenario: str,
    ) -> AlertScenarioSource | None:

        for source in self._sources.values():
            if (
                source.scenario == scenario
                and source.status == "RUNNING"
            ):
                return source

        return None

    # ==================================================================
    # Generator
    # ==================================================================

    async def _run_source(
        self,
        source_id: str,
    ) -> None:

        while True:
            source = self._sources.get(
                source_id
            )

            if source is None:
                return

            if source.status != "RUNNING":
                return

            index = source.sample_index

            timestamp = (
                source.spoof_timestamp
                + timedelta(
                    seconds=(
                        index
                        * source.interval_seconds
                    )
                )
            )

            metrics = self.scenario_metrics(
                source.scenario,
                index=index,
            )

            reading = VitalReading(
                source_id=source.source_id,
                patient_id=source.patient_id,
                encounter_id=source.encounter_id,
                device_id=source.device_id,
                timestamp=timestamp,
                metrics=metrics,
            )

            updated_source = source.model_copy(
                update={
                    "sample_index": index + 1,
                    "last_reading": reading,
                }
            )

            self._sources[
                source_id
            ] = updated_source

            await self._publish_reading(
                reading
            )

            print(
                "[DEMO THRESHOLD]",
                reading.model_dump(
                    mode="json"
                ),
            )

            await asyncio.sleep(
                source.interval_seconds
            )

    # ==================================================================
    # Publish
    # ==================================================================

    async def _publish_reading(
        self,
        reading: VitalReading,
    ) -> None:

        await self._kafka_producer.publish(
            topic=settings.kafka_vitals_topic,
            key=reading.patient_id,
            payload=reading.model_dump(
                mode="json"
            ),
        )

    # ==================================================================
    # Scenario values
    # ==================================================================

    @classmethod
    def scenario_metrics(
        cls,
        scenario: str,
        index: int = 5,
    ) -> dict[str, float]:

        scenario = (
            scenario.strip().lower()
        )

        if scenario not in cls.ALL_SCENARIOS:
            raise ValueError(
                f"Unknown alert scenario: {scenario}"
            )

        return cls._scenario_metrics(
            scenario,
            index,
        )

    @classmethod
    def _scenario_metrics(
        cls,
        scenario: str,
        index: int,
    ) -> dict[str, float]:

        metrics = dict(
            cls.BASELINE
        )

        # --------------------------------------------------------------
        # Seed
        # --------------------------------------------------------------

        if scenario in cls.SEED_SCENARIOS:

            if index < 5:
                return metrics

            cls._apply_seed(
                metrics,
                scenario,
            )

            return metrics

        # --------------------------------------------------------------
        # Threshold
        # --------------------------------------------------------------

        if scenario in cls.THRESHOLD_SCENARIOS:

            metric_name, value = (
                cls.THRESHOLD_VALUES[
                    scenario
                ]
            )

            metrics[
                metric_name
            ] = value

            return metrics

        # --------------------------------------------------------------
        # Trend
        # --------------------------------------------------------------

        if scenario in cls.TREND_SCENARIOS:

            metric_name, target = (
                cls.TREND_TARGETS[
                    scenario
                ]
            )

            start_index = 5
            ramp_length = 20

            if index < start_index:
                return metrics

            progress = min(
                1.0,
                (
                    index
                    - start_index
                )
                / ramp_length,
            )

            start_value = cls.BASELINE[
                metric_name
            ]

            value = (
                start_value
                + (
                    target
                    - start_value
                )
                * progress
            )

            metrics[
                metric_name
            ] = round(
                value,
                2,
            )

            return metrics

        return metrics

    # ==================================================================
    # Seed scenario values
    # ==================================================================

    @staticmethod
    def _apply_seed(
        metrics: dict[str, float],
        scenario: str,
    ) -> None:

        values = {
            "spo2_drop": (
                "spo2",
                91.0,
            ),

            "hr_drop": (
                "heart_rate",
                40.0,
            ),

            "hr_rise": (
                "heart_rate",
                130.0,
            ),

            "temperature_drop": (
                "temperature",
                35.0,
            ),

            "temperature_rise": (
                "temperature",
                39.0,
            ),

            "respiratory_rate_drop": (
                "respiratory_rate",
                8.0,
            ),

            "respiratory_rate_rise": (
                "respiratory_rate",
                28.0,
            ),

            "systolic_bp_drop": (
                "systolic_bp",
                85.0,
            ),

            "systolic_bp_rise": (
                "systolic_bp",
                190.0,
            ),

            "diastolic_bp_drop": (
                "diastolic_bp",
                45.0,
            ),

            "diastolic_bp_rise": (
                "diastolic_bp",
                115.0,
            ),
        }

        metric_name, value = values[
            scenario
        ]

        metrics[
            metric_name
        ] = value

    # ==================================================================
    # Shutdown
    # ==================================================================

    async def shutdown(self) -> None:

        tasks = list(
            self._tasks.items()
        )

        self._tasks.clear()

        for source_id, task in tasks:
            task.cancel()

            try:
                await task

            except asyncio.CancelledError:
                pass

        for source_id, source in list(
            self._sources.items()
        ):
            self._sources[
                source_id
            ] = source.model_copy(
                update={
                    "status": "STOPPED",
                }
            )