import requests


MIDDLEWARE_URL = "http://localhost:8000"


class MiddlewareError(Exception):
    pass


def _request(
    method: str,
    path: str,
    *,
    json: dict | None = None,
):
    try:
        response = requests.request(
            method=method,
            url=f"{MIDDLEWARE_URL}{path}",
            json=json,
            timeout=10,
        )

    except requests.RequestException as exc:
        raise MiddlewareError(
            f"Could not connect to clinical middleware: {exc}"
        ) from exc

    if not response.ok:
        try:
            detail = response.json().get(
                "detail",
                response.text,
            )
        except Exception:
            detail = response.text

        raise MiddlewareError(
            f"Middleware request failed "
            f"({response.status_code}): {detail}"
        )

    if not response.content:
        return None

    return response.json()


# =========================================================
# SYSTEM
# =========================================================

def get_health():
    return _request(
        "GET",
        "/health",
    )


# =========================================================
# PATIENTS
# =========================================================

def register_patient(
    payload: dict,
):
    return _request(
        "POST",
        "/patients",
        json=payload,
    )


def list_patients():
    return _request(
        "GET",
        "/patients",
    )


def get_patient(
    patient_id: str,
):
    return _request(
        "GET",
        f"/patients/{patient_id}",
    )


# =========================================================
# ENCOUNTERS
# =========================================================

def start_encounter(
    payload: dict,
):
    return _request(
        "POST",
        "/encounters",
        json=payload,
    )


def get_encounter(
    encounter_id: str,
):
    return _request(
        "GET",
        f"/encounters/{encounter_id}",
    )


def close_encounter(
    encounter_id: str,
    payload: dict,
):
    return _request(
        "POST",
        f"/encounters/{encounter_id}/close",
        json=payload,
    )


# =========================================================
# EPISODES
# =========================================================

def start_episode_from_journal(
    payload: dict,
):
    return _request(
        "POST",
        "/episodes/from-journal",
        json=payload,
    )


def get_episode(
    episode_id: str,
):
    return _request(
        "GET",
        f"/episodes/{episode_id}",
    )


def close_episode(
    episode_id: str,
    payload: dict,
):
    return _request(
        "POST",
        f"/episodes/{episode_id}/close",
        json=payload,
    )


# =========================================================
# JOURNALS
# =========================================================

def create_journal_event(
    payload: dict,
):
    return _request(
        "POST",
        "/journals/event",
        json=payload,
    )


def create_fixed_journal_activity(
    payload: dict,
):
    return _request(
        "POST",
        "/journals/activity/fixed",
        json=payload,
    )


def start_ongoing_journal_activity(
    payload: dict,
):
    return _request(
        "POST",
        "/journals/activity/ongoing",
        json=payload,
    )


def end_ongoing_journal_activity(
    journal_id: str,
    payload: dict,
):
    return _request(
        "POST",
        f"/journals/activity/ongoing/{journal_id}/end",
        json=payload,
    )