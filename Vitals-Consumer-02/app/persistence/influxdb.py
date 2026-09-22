from datetime import datetime

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import settings


class InfluxVitalsWriter:
    MEASUREMENT = "vitals"

    FIELD_NAMES = {
        "spo2",
        "heart_rate",
        "temperature",
        "respiratory_rate",
        "systolic_bp",
        "diastolic_bp",
    }

    def __init__(self):
        self._client = InfluxDBClient(
            url=settings.influx_url,
            token=settings.influx_token,
            org=settings.influx_org,
        )

        self._write_api = self._client.write_api(
            write_options=SYNCHRONOUS,
        )

    def close(self) -> None:
        self._write_api.close()
        self._client.close()

    def write(
        self,
        *,
        patient_id: str,
        encounter_id: str,
        device_id: str,
        timestamp: datetime,
        metrics: dict[str, float],
    ) -> None:

        fields = {
            name: value
            for name, value in metrics.items()
            if name in self.FIELD_NAMES
        }

        if not fields:
            raise ValueError(
                "Vital reading contains none of the "
                "contract-defined fields."
            )

        point = (
            Point(self.MEASUREMENT)
            .tag("patient_id", patient_id)
            .tag("encounter_id", encounter_id)
            .tag("device_id", device_id)
            .time(timestamp)
        )

        for field_name, value in fields.items():
            point.field(field_name, value)

        self._write_api.write(
            bucket=settings.influx_bucket,
            org=settings.influx_org,
            record=point,
        )