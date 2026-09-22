from pprint import pprint

from fastapi import APIRouter, Request

from app.services.alarm_service import alarm_service


router = APIRouter(
    prefix="/webhooks/grafana",
    tags=["grafana"],
)


@router.post(
    "/alerts",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "example": {
                        "status": "firing",
                        "alerts": [
                            {
                                "status": "firing",
                                "labels": {
                                    "alertname": "spo2_high_low",
                                    "encounter_id": "E1",
                                    "device_id": "DEV-001",
                                },
                                "annotations": {},
                                "startsAt": "2026-09-21T14:39:20Z",
                                "endsAt": "0001-01-01T00:00:00Z",
                                "values": {
                                    "B": 91.0,
                                },
                                "fingerprint": "example-fingerprint",
                            }
                        ],
                    },
                }
            },
        }
    },
)
async def receive_grafana_alert(
    request: Request,
):
    payload = await request.json()

    print("\n================ GRAFANA ALERT ================")
    pprint(payload)
    print("================================================\n")

    alarm_service.process_grafana_payload(payload)

    return {
        "status": "received",
    }