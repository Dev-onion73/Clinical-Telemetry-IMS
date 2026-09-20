import requests


MIDDLEWARE_URL = "http://localhost:8000"


def register_patient(payload: dict):
    response = requests.post(
        f"{MIDDLEWARE_URL}/patients",
        json=payload,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()