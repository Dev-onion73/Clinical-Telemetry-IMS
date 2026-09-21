import asyncio
import json
from contextlib import suppress

from app.messaging.kafka import KafkaConsumer
from app.persistence.influxdb import InfluxVitalsWriter
from app.schemas.vitals import VitalReading


async def run() -> None:
    consumer = KafkaConsumer()
    influx_writer = InfluxVitalsWriter()

    print("Vitals Consumer starting...")

    await consumer.start()

    print("Kafka consumer started.")
    print("Listening for clinical.vitals...")

    try:
        async for payload in consumer.messages():
            print(
                "[KAFKA VITAL]",
                json.dumps(
                    payload,
                    indent=2,
                ),
            )

            try:
                reading = VitalReading.model_validate(
                    payload
                )

                influx_writer.write(
                    patient_id=reading.patient_id,
                    encounter_id=reading.encounter_id,
                    device_id=reading.device_id,
                    timestamp=reading.timestamp,
                    metrics=reading.metrics,
                )

                print(
                    "[INFLUXDB] wrote reading "
                    f"for {reading.patient_id}"
                )

            except Exception as exc:
                print(
                    "[VITAL ERROR]",
                    repr(exc),
                )

    finally:
        print("Vitals Consumer shutting down...")

        with suppress(asyncio.CancelledError):
            await consumer.stop()

        influx_writer.close()

        print("Vitals Consumer stopped.")


if __name__ == "__main__":
    asyncio.run(run())