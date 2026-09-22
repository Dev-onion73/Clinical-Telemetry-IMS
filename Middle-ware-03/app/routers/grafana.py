from pprint import pprint

from fastapi import APIRouter, Request


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
                                    "patient_id": "PAT-0001",
                                    "encounter_id": "E1",
                                    "device_id": "DEV-001",
                                },
                                "annotations": {},
                                "startsAt": "2026-09-21T14:39:20Z",
                                "endsAt": "0001-01-01T00:00:00Z",
                                "values": {
                                    "B": 91.0
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

    print()
    print("=" * 80)
    print("[GRAFANA WEBHOOK] ALERT RECEIVED")
    print("=" * 80)

    pprint(
        payload,
        sort_dicts=False,
        width=120,
    )

    print("=" * 80)
    print()

    return {
        "status": "received",
    }