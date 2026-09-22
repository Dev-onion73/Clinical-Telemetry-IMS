from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from app.messaging.kafka import KafkaProducer
from app.schemas.alerts import (
    AlertInjectionResponse,
    ScenarioType,
)
from app.schemas.vitals import VitalReading
from app.services.alert_scenarios import (
    AlertScenarioService,
)


class AlertInjectorService:
    def __init__(
        self,
        kafka_producer: KafkaProducer,
        alert_scenario_service: AlertScenarioService,
    ):
        self._kafka_producer = kafka_producer
        self._alert_scenario_service = (
            alert_scenario_service
        )

    # ==================================================================
    # One-shot injection
    # ==================================================================

    async def inject(
        self,
        *,
        scenario: str,
        patient_id: str,
        encounter_id: str,
        device_id: str,
        spoof_timestamp: datetime | None = None,
    ) -> AlertInjectionResponse:

        scenario = (
            scenario.strip().lower()
        )

        scenario_type = (
            self._alert_scenario_service.scenario_type(
                scenario
            )
        )

        if scenario_type == ScenarioType.THRESHOLD:
            raise ValueError(
                "Threshold scenarios must be started "
                "through the continuous threshold endpoint."
            )

        if spoof_timestamp is None:
            spoof_timestamp = datetime.now(
                timezone.utc
            )

        injection_id = (
            f"INJ-{uuid4().hex[:8].upper()}"
        )

        source_id = (
            f"DEMO-{uuid4().hex[:8].upper()}"
        )

        metrics = (
            self._alert_scenario_service.scenario_metrics(
                scenario,
                index=5,
            )
        )

        reading = VitalReading(
            source_id=source_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            device_id=device_id,
            timestamp=spoof_timestamp,
            metrics=metrics,
        )

        await self._kafka_producer.publish(
            topic=settings.kafka_vitals_topic,
            key=patient_id,
            payload=reading.model_dump(
                mode="json"
            ),
        )

        injected_at = datetime.now(
            timezone.utc
        )

        result = AlertInjectionResponse(
            injection_id=injection_id,
            source_id=source_id,
            scenario=scenario,
            scenario_type=scenario_type.value,
            status="INJECTED",
            spoof_timestamp=spoof_timestamp,
            injected_at=injected_at,
            message=(
                f"Instantaneous {scenario_type.value} "
                f"scenario '{scenario}' injected."
            ),
        )

        print(
            "[DEMO ALERT]",
            {
                "injection_id": injection_id,
                "source_id": source_id,
                "scenario": scenario,
                "scenario_type": scenario_type.value,
                "spoof_timestamp": spoof_timestamp.isoformat(),
                "actual_injected_at": injected_at.isoformat(),
                "metrics": metrics,
            },
        )

        return result

    # ==================================================================
    # Shutdown
    # ==================================================================

    async def shutdown(self) -> None:
        return