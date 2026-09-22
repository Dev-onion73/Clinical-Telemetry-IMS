from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st

from api import TestingBackendAPI


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_BACKEND_URL = "http://127.0.0.1:8010"

BASELINE = {
    "spo2": 98.0,
    "heart_rate": 80.0,
    "temperature": 37.0,
    "respiratory_rate": 16.0,
    "systolic_bp": 120.0,
    "diastolic_bp": 80.0,
}

VITAL_PRESETS = {
    "Normal baseline": {
        "spo2": 98.0,
        "heart_rate": 80.0,
        "temperature": 37.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
    },
    "Low SpO2": {
        "spo2": 91.0,
        "heart_rate": 80.0,
        "temperature": 37.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
    },
    "High heart rate": {
        "spo2": 98.0,
        "heart_rate": 130.0,
        "temperature": 37.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
    },
    "Low blood pressure": {
        "spo2": 98.0,
        "heart_rate": 80.0,
        "temperature": 37.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 85.0,
        "diastolic_bp": 45.0,
    },
    "High blood pressure": {
        "spo2": 98.0,
        "heart_rate": 80.0,
        "temperature": 37.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 190.0,
        "diastolic_bp": 115.0,
    },
    "High temperature": {
        "spo2": 98.0,
        "heart_rate": 80.0,
        "temperature": 39.0,
        "respiratory_rate": 16.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
    },
}


# Streamlit's datetime_input requires a step between 60 seconds
# and 23 hours. This controls only the UI picker.
#
# It does NOT control the backend threshold generation interval.
DATETIME_INPUT_STEP = timedelta(minutes=1)


# ============================================================================
# Streamlit
# ============================================================================

st.set_page_config(
    page_title="Testing Backend",
    page_icon="🧪",
    layout="wide",
)

st.title("Testing Backend — Synthetic Clinical Data Console")

st.caption(
    "Synthetic clinical-data generator and alert injector. "
    "Grafana remains responsible for alert evaluation."
)


# ============================================================================
# Session state
# ============================================================================

def init_state() -> None:
    defaults = {
        "backend_url": DEFAULT_BACKEND_URL,
        "alert_catalog": None,
        "recent_activity": [],
        "last_health": None,

        # Clinical context.
        "context_patient_id": "PAT-0001",
        "context_encounter_id": "E1",
        "context_device_id": "DEV-001",

        # Vitals.
        "vital_interval": 1.0,
        "vital_start_time": datetime.now(),
        "vital_preset": "Normal baseline",
        "vital_spo2": BASELINE["spo2"],
        "vital_heart_rate": BASELINE["heart_rate"],
        "vital_temperature": BASELINE["temperature"],
        "vital_respiratory_rate": BASELINE["respiratory_rate"],
        "vital_systolic_bp": BASELINE["systolic_bp"],
        "vital_diastolic_bp": BASELINE["diastolic_bp"],

        # Alert selection.
        "selected_alerts": [],
        "single_alert_category": "threshold",
        "single_alert_scenario": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# ============================================================================
# Helpers
# ============================================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()


def add_activity(kind: str, result: Any) -> None:
    st.session_state.recent_activity.insert(
        0,
        {
            "time": utc_now().isoformat(),
            "kind": kind,
            "result": result,
        },
    )

    st.session_state.recent_activity = (
        st.session_state.recent_activity[:100]
    )


def show_error(exc: Exception) -> None:
    st.error(str(exc))


def safe_scenario_key(scenario: str) -> str:
    return scenario.replace("-", "_")


def catalog_to_scenarios(catalog: Any) -> dict[str, list[str]]:
    normalized = {
        "seed": [],
        "threshold": [],
        "trend": [],
    }

    if not isinstance(catalog, dict):
        return normalized

    for category in normalized:
        value = catalog.get(category, [])

        if isinstance(value, dict):
            value = list(value.keys())

        if not isinstance(value, list):
            continue

        for item in value:
            if isinstance(item, str):
                normalized[category].append(item)

            elif isinstance(item, dict):
                scenario = (
                    item.get("scenario")
                    or item.get("name")
                    or item.get("id")
                )

                if scenario:
                    normalized[category].append(str(scenario))

    return normalized


def all_scenarios(
    catalog: dict[str, list[str]],
) -> list[str]:
    result = []

    for category in ("seed", "threshold", "trend"):
        result.extend(catalog.get(category, []))

    return result


def scenario_category(
    scenario: str,
    catalog: dict[str, list[str]],
) -> str:
    for category, scenarios in catalog.items():
        if scenario in scenarios:
            return category

    return "unknown"


def initialize_alert_state(
    scenarios: list[str],
) -> None:
    for scenario in scenarios:
        safe = safe_scenario_key(scenario)

        defaults = {
            f"single_alert_spoof_{safe}": datetime.now(),
            f"selected_alert_spoof_{safe}": datetime.now(),
            f"all_alert_spoof_{safe}": datetime.now(),
            f"alert_status_{safe}": "NOT LAUNCHED",
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value


def set_alert_status(
    scenario: str,
    status: str,
) -> None:
    safe = safe_scenario_key(scenario)

    st.session_state[
        f"alert_status_{safe}"
    ] = status


def alert_status(scenario: str) -> str:
    safe = safe_scenario_key(scenario)

    return st.session_state.get(
        f"alert_status_{safe}",
        "NOT LAUNCHED",
    )


def apply_vital_preset(
    preset_name: str,
) -> None:
    values = VITAL_PRESETS[preset_name]

    st.session_state["vital_spo2"] = values["spo2"]
    st.session_state["vital_heart_rate"] = values["heart_rate"]
    st.session_state["vital_temperature"] = values["temperature"]
    st.session_state["vital_respiratory_rate"] = values[
        "respiratory_rate"
    ]
    st.session_state["vital_systolic_bp"] = values[
        "systolic_bp"
    ]
    st.session_state["vital_diastolic_bp"] = values[
        "diastolic_bp"
    ]


# ============================================================================
# Threshold helpers
# ============================================================================

def get_threshold_sources(
    api: TestingBackendAPI,
) -> list[dict[str, Any]]:
    try:
        result = api.get_threshold_sources()

    except Exception:
        return []

    if not isinstance(result, list):
        return []

    return result


def get_running_threshold(
    api: TestingBackendAPI,
    scenario: str,
) -> dict[str, Any] | None:
    for source in get_threshold_sources(api):
        if (
            source.get("scenario") == scenario
            and source.get("status") == "RUNNING"
        ):
            return source

    return None


def start_threshold(
    api: TestingBackendAPI,
    *,
    scenario: str,
    patient_id: str,
    encounter_id: str,
    device_id: str,
    interval_seconds: float,
    spoof_timestamp: str | None,
) -> dict[str, Any]:

    result = api.start_threshold(
        scenario=scenario,
        patient_id=patient_id,
        encounter_id=encounter_id,
        device_id=device_id,
        start_time=datetime_to_iso(datetime.now()),
        interval_seconds=interval_seconds,
        spoof_timestamp=spoof_timestamp,
    )

    set_alert_status(
        scenario,
        "RUNNING",
    )

    add_activity(
        "THRESHOLD START",
        result,
    )

    return result


def stop_threshold(
    api: TestingBackendAPI,
    *,
    scenario: str,
    source_id: str,
) -> dict[str, Any]:

    result = api.stop_threshold(source_id)

    set_alert_status(
        scenario,
        result.get(
            "status",
            "STOPPED",
        ),
    )

    add_activity(
        "THRESHOLD STOP",
        result,
    )

    return result


def render_threshold_controls(
    api: TestingBackendAPI,
    *,
    scenario: str,
    patient_id: str,
    encounter_id: str,
    device_id: str,
    interval_seconds: float,
    spoof_timestamp: str | None,
    button_prefix: str,
    compact: bool = False,
) -> None:

    safe = safe_scenario_key(scenario)

    running = get_running_threshold(
        api,
        scenario,
    )

    if running:
        source_id = running.get(
            "source_id",
            "unknown",
        )

        if compact:
            st.success(
                f"RUNNING · `{source_id}`"
            )
        else:
            st.success(
                f"Threshold running: `{source_id}`"
            )

            st.caption(
                f"Interval: "
                f"{running.get('interval_seconds', '-')}"
                " seconds"
            )

            reading = running.get(
                "last_reading"
            )

            if reading:
                metrics = reading.get(
                    "metrics",
                    {},
                )

                st.write(
                    " | ".join(
                        f"{name}={value}"
                        for name, value in metrics.items()
                    )
                )

                st.caption(
                    f"Last reading: "
                    f"{reading.get('timestamp', '-')}"
                )

        if st.button(
            "Stop" if compact else "Stop threshold",
            key=f"{button_prefix}_stop_{safe}",
            use_container_width=True,
        ):
            try:
                result = stop_threshold(
                    api,
                    scenario=scenario,
                    source_id=source_id,
                )

                st.success(
                    f"Stopped `{source_id}`."
                )

                st.rerun()

            except Exception as exc:
                show_error(exc)

    else:
        if st.button(
            "Start" if compact else "Start threshold",
            type="primary",
            key=f"{button_prefix}_start_{safe}",
            use_container_width=True,
        ):
            try:
                result = start_threshold(
                    api,
                    scenario=scenario,
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    device_id=device_id,
                    interval_seconds=interval_seconds,
                    spoof_timestamp=spoof_timestamp,
                )

                st.success(
                    f"Started `{result['source_id']}`."
                )

                st.rerun()

            except Exception as exc:
                show_error(exc)


def stop_all_thresholds(
    api: TestingBackendAPI,
) -> tuple[int, int]:

    stopped = 0
    failed = 0

    for source in get_threshold_sources(api):
        if source.get("status") != "RUNNING":
            continue

        source_id = source.get("source_id")
        scenario = source.get("scenario")

        if not source_id:
            continue

        try:
            result = api.stop_threshold(
                source_id
            )

            if scenario:
                set_alert_status(
                    scenario,
                    result.get(
                        "status",
                        "STOPPED",
                    ),
                )

            add_activity(
                "THRESHOLD STOP ALL",
                result,
            )

            stopped += 1

        except Exception as exc:
            failed += 1

            add_activity(
                "THRESHOLD STOP ALL ERROR",
                {
                    "source_id": source_id,
                    "scenario": scenario,
                    "error": str(exc),
                },
            )

    return stopped, failed


# ============================================================================
# Backend
# ============================================================================

with st.sidebar:
    st.header("Backend")

    st.text_input(
        "Backend URL",
        key="backend_url",
    )

    api = TestingBackendAPI(
        st.session_state.backend_url
    )

    if st.button(
        "Check backend",
        use_container_width=True,
        key="check_backend",
    ):
        try:
            result = api.health()

            st.session_state.last_health = result

            st.success(
                "Backend reachable."
            )

        except Exception as exc:
            st.session_state.last_health = None
            st.error(
                f"Backend unavailable: {exc}"
            )

    if st.session_state.last_health:
        st.json(
            st.session_state.last_health
        )


api = TestingBackendAPI(
    st.session_state.backend_url
)


# ============================================================================
# Alert catalog
# ============================================================================

if st.session_state.alert_catalog is None:
    try:
        st.session_state.alert_catalog = (
            api.get_alert_catalog()
        )

    except Exception as exc:
        st.warning(
            "Could not load the alert catalog yet. "
            f"Backend error: {exc}"
        )


catalog = catalog_to_scenarios(
    st.session_state.alert_catalog
    if st.session_state.alert_catalog is not None
    else {}
)

scenarios = all_scenarios(catalog)

if scenarios:
    initialize_alert_state(scenarios)


# ============================================================================
# Clinical context
# ============================================================================

st.header("Clinical Context")

context_col1, context_col2, context_col3 = st.columns(3)

with context_col1:
    patient_id = st.text_input(
        "Patient ID",
        key="context_patient_id",
    )

with context_col2:
    encounter_id = st.text_input(
        "Encounter ID",
        key="context_encounter_id",
    )

with context_col3:
    device_id = st.text_input(
        "Device ID",
        key="context_device_id",
    )


# ============================================================================
# VITALS
# ============================================================================

st.divider()
st.header("Vitals Generator")

preset_col, interval_col, start_col = st.columns(3)

with preset_col:
    st.selectbox(
        "Vitals preset",
        list(VITAL_PRESETS.keys()),
        key="vital_preset",
    )

    if st.button(
        "Apply preset",
        key="apply_vital_preset",
        use_container_width=True,
    ):
        apply_vital_preset(
            st.session_state.vital_preset
        )
        st.rerun()

with interval_col:
    interval_seconds = st.number_input(
        "Interval (seconds)",
        min_value=0.1,
        max_value=3600.0,
        step=0.1,
        key="vital_interval",
    )

with start_col:
    start_time = st.datetime_input(
        "Start timestamp",
        key="vital_start_time",
        step=DATETIME_INPUT_STEP,
    )


st.subheader("Metrics")

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    spo2 = st.number_input(
        "SpO₂",
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        key="vital_spo2",
    )

    heart_rate = st.number_input(
        "Heart rate",
        min_value=0.0,
        max_value=300.0,
        step=1.0,
        key="vital_heart_rate",
    )

with metric_col2:
    temperature = st.number_input(
        "Temperature",
        min_value=20.0,
        max_value=45.0,
        step=0.1,
        key="vital_temperature",
    )

    respiratory_rate = st.number_input(
        "Respiratory rate",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        key="vital_respiratory_rate",
    )

with metric_col3:
    systolic_bp = st.number_input(
        "Systolic BP",
        min_value=0.0,
        max_value=300.0,
        step=1.0,
        key="vital_systolic_bp",
    )

    diastolic_bp = st.number_input(
        "Diastolic BP",
        min_value=0.0,
        max_value=250.0,
        step=1.0,
        key="vital_diastolic_bp",
    )


metrics = {
    "spo2": spo2,
    "heart_rate": heart_rate,
    "temperature": temperature,
    "respiratory_rate": respiratory_rate,
    "systolic_bp": systolic_bp,
    "diastolic_bp": diastolic_bp,
}


if st.button(
    "Start stable vitals",
    type="primary",
    key="start_vitals",
    use_container_width=True,
):
    try:
        result = api.start_stable_vitals(
            patient_id=patient_id,
            encounter_id=encounter_id,
            device_id=device_id,
            start_time=datetime_to_iso(start_time),
            metrics=metrics,
            interval_seconds=interval_seconds,
        )

        add_activity(
            "VITALS START",
            result,
        )

        st.success(
            "Started vitals source "
            f"`{result.get('source_id', 'unknown')}`."
        )

    except Exception as exc:
        show_error(exc)


# ============================================================================
# Active vital sources
# ============================================================================

st.subheader("Running / Previous Vital Sources")

if st.button(
    "Refresh vital sources",
    key="refresh_vital_sources",
):
    st.rerun()


try:
    vital_sources = api.get_stable_vitals()

except Exception as exc:
    vital_sources = []

    st.warning(
        f"Could not load vital sources: {exc}"
    )


if not vital_sources:
    st.info(
        "No vital sources currently known."
    )

else:
    for source in vital_sources:
        source_id = source.get(
            "source_id",
            "unknown",
        )

        status = source.get(
            "status",
            "UNKNOWN",
        )

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(
                [2, 2, 3, 1]
            )

            with col1:
                st.markdown(
                    f"**{source_id}**"
                )

                st.caption(
                    f"{source.get('patient_id', '-')} / "
                    f"{source.get('encounter_id', '-')}"
                )

            with col2:
                st.write(
                    f"Device: `{source.get('device_id', '-')}`"
                )

                st.write(
                    f"Status: **{status}**"
                )

            with col3:
                reading = source.get(
                    "last_reading"
                )

                if reading:
                    reading_metrics = reading.get(
                        "metrics",
                        {},
                    )

                    st.write(
                        " | ".join(
                            f"{name}={value}"
                            for name, value in reading_metrics.items()
                        )
                    )

                    st.caption(
                        "Last reading: "
                        f"{reading.get('timestamp', '-')}"
                    )

                else:
                    st.caption(
                        "No reading yet."
                    )

            with col4:
                if status == "RUNNING":
                    if st.button(
                        "Stop",
                        key=f"stop_vitals_{source_id}",
                        use_container_width=True,
                    ):
                        try:
                            result = (
                                api.stop_stable_vitals(
                                    source_id
                                )
                            )

                            add_activity(
                                "VITALS STOP",
                                result,
                            )

                            st.success(
                                f"Stopped {source_id}."
                            )

                            st.rerun()

                        except Exception as exc:
                            show_error(exc)


# ============================================================================
# SINGLE ALERT
# ============================================================================

st.divider()
st.header("Single Alert Injection")

if not scenarios:
    st.warning(
        "No alert scenarios are available. "
        "Check that the Testing Backend is running."
    )

else:
    category_col, scenario_col = st.columns(
        [1, 2]
    )

    with category_col:
        category = st.selectbox(
            "Alert category",
            ["seed", "threshold", "trend"],
            key="single_alert_category",
        )

    available_scenarios = catalog.get(
        category,
        [],
    )

    with scenario_col:
        if available_scenarios:
            selected_scenario = st.selectbox(
                "Scenario",
                available_scenarios,
                key="single_alert_scenario",
            )
        else:
            selected_scenario = None

            st.warning(
                f"No {category} scenarios available."
            )

    if selected_scenario:
        safe = safe_scenario_key(
            selected_scenario
        )

        # ------------------------------------------------------------
        # Threshold = continuous Start / Stop.
        # ------------------------------------------------------------

        if category == "threshold":
            st.info(
                "Threshold scenarios are continuous. "
                "The click starts emission immediately. "
                "The spoof timestamp is used as the clinical "
                "timestamp basis. Stop manually to end the condition."
            )

            threshold_spoof = st.datetime_input(
                "Spoof timestamp",
                key=f"single_threshold_spoof_{safe}",
                step=DATETIME_INPUT_STEP,
                format="YYYY/MM/DD",
            )

            threshold_interval = st.number_input(
                "Threshold interval (seconds)",
                min_value=0.1,
                max_value=3600.0,
                value=1.0,
                step=0.1,
                key=f"single_threshold_interval_{safe}",
            )

            render_threshold_controls(
                api,
                scenario=selected_scenario,
                patient_id=patient_id,
                encounter_id=encounter_id,
                device_id=device_id,
                interval_seconds=threshold_interval,
                spoof_timestamp=datetime_to_iso(
                    threshold_spoof
                ),
                button_prefix="single_threshold",
            )

        # ------------------------------------------------------------
        # Seed / Trend = instantaneous one-shot.
        # ------------------------------------------------------------

        else:
            spoof_value = st.datetime_input(
                "Spoof timestamp",
                key=f"single_alert_spoof_{safe}",
                step=DATETIME_INPUT_STEP,
                format="YYYY/MM/DD",
            )

            st.caption(
                "The alert is injected immediately when you click "
                "the button. This timestamp only controls the "
                "timestamp carried by the generated data."
            )

            if st.button(
                "Inject alert",
                type="primary",
                key="inject_single_alert",
                use_container_width=True,
            ):
                try:
                    result = api.inject_alert(
                        scenario=selected_scenario,
                        patient_id=patient_id,
                        encounter_id=encounter_id,
                        device_id=device_id,
                        spoof_timestamp=datetime_to_iso(
                            spoof_value
                        ),
                    )

                    set_alert_status(
                        selected_scenario,
                        result.get(
                            "status",
                            "SUBMITTED",
                        ),
                    )

                    add_activity(
                        "SINGLE ALERT",
                        result,
                    )

                    st.success(
                        result.get(
                            "message",
                            "Alert submitted.",
                        )
                    )

                except Exception as exc:
                    show_error(exc)


# ============================================================================
# SELECTED ALERTS
# ============================================================================

st.divider()
st.header("Selected Alerts")

if scenarios:
    selected_alerts = st.multiselect(
        "Choose alert scenarios",
        options=scenarios,
        key="selected_alerts",
    )

    if selected_alerts:
        st.caption(
            f"{len(selected_alerts)} alert(s) selected."
        )

        for scenario in selected_alerts:
            category = scenario_category(
                scenario,
                catalog,
            )

            safe = safe_scenario_key(
                scenario
            )

            with st.container(border=True):

                if category == "threshold":
                    col1, col2, col3 = st.columns(
                        [2.5, 2.5, 1.5]
                    )

                    with col1:
                        st.markdown(
                            f"**{scenario}**"
                        )

                        st.caption(
                            "THRESHOLD · CONTINUOUS"
                        )

                    with col2:
                        selected_threshold_spoof = (
                            st.datetime_input(
                                "Spoof",
                                key=(
                                    f"selected_threshold_spoof_{safe}"
                                ),
                                step=DATETIME_INPUT_STEP,
                                format="YYYY/MM/DD",
                            )
                        )

                        selected_threshold_interval = (
                            st.number_input(
                                "Interval",
                                min_value=0.1,
                                max_value=3600.0,
                                value=1.0,
                                step=0.1,
                                key=(
                                    f"selected_threshold_interval_{safe}"
                                ),
                            )
                        )

                    with col3:
                        render_threshold_controls(
                            api,
                            scenario=scenario,
                            patient_id=patient_id,
                            encounter_id=encounter_id,
                            device_id=device_id,
                            interval_seconds=(
                                selected_threshold_interval
                            ),
                            spoof_timestamp=(
                                datetime_to_iso(
                                    selected_threshold_spoof
                                )
                            ),
                            button_prefix="selected_threshold",
                            compact=True,
                        )

                else:
                    col1, col2 = st.columns(
                        [2, 3]
                    )

                    with col1:
                        st.markdown(
                            f"**{scenario}**"
                        )

                        st.caption(
                            category.upper()
                        )

                        st.caption(
                            alert_status(scenario)
                        )

                    with col2:
                        st.datetime_input(
                            "Spoof timestamp",
                            key=(
                                f"selected_alert_spoof_{safe}"
                            ),
                            step=DATETIME_INPUT_STEP,
                            format="YYYY/MM/DD",
                        )

                        if st.button(
                            "Inject this alert",
                            key=f"inject_selected_{safe}",
                        ):
                            try:
                                spoof_value = (
                                    st.session_state[
                                        f"selected_alert_spoof_{safe}"
                                    ]
                                )

                                result = api.inject_alert(
                                    scenario=scenario,
                                    patient_id=patient_id,
                                    encounter_id=encounter_id,
                                    device_id=device_id,
                                    spoof_timestamp=(
                                        datetime_to_iso(
                                            spoof_value
                                        )
                                    ),
                                )

                                set_alert_status(
                                    scenario,
                                    result.get(
                                        "status",
                                        "SUBMITTED",
                                    ),
                                )

                                add_activity(
                                    "SELECTED ALERT",
                                    result,
                                )

                                st.success(
                                    result.get(
                                        "message",
                                        "Alert submitted.",
                                    )
                                )

                            except Exception as exc:
                                show_error(exc)

        # ------------------------------------------------------------
        # Selected bulk threshold controls.
        # ------------------------------------------------------------

        st.subheader("Selected bulk actions")

        selected_thresholds = [
            scenario
            for scenario in selected_alerts
            if scenario_category(
                scenario,
                catalog,
            ) == "threshold"
        ]

        selected_one_shots = [
            scenario
            for scenario in selected_alerts
            if scenario_category(
                scenario,
                catalog,
            ) != "threshold"
        ]

        selected_bulk_spoof = st.datetime_input(
            "Spoof timestamp for selected thresholds",
            value=datetime.now(),
            key="selected_bulk_threshold_spoof",
            step=DATETIME_INPUT_STEP,
            format="YYYY/MM/DD",
        )

        selected_bulk_interval = st.number_input(
            "Interval for selected thresholds (seconds)",
            min_value=0.1,
            max_value=3600.0,
            value=1.0,
            step=0.1,
            key="selected_bulk_threshold_interval",
        )

        bulk_col1, bulk_col2, bulk_col3 = st.columns(3)

        with bulk_col1:
            if selected_thresholds:
                if st.button(
                    "Start selected thresholds",
                    type="primary",
                    key="start_selected_thresholds",
                    use_container_width=True,
                ):
                    successes = 0
                    failures = 0

                    for scenario in selected_thresholds:
                        try:
                            if get_running_threshold(
                                api,
                                scenario,
                            ):
                                continue

                            start_threshold(
                                api,
                                scenario=scenario,
                                patient_id=patient_id,
                                encounter_id=encounter_id,
                                device_id=device_id,
                                interval_seconds=(
                                    selected_bulk_interval
                                ),
                                spoof_timestamp=(
                                    datetime_to_iso(
                                        selected_bulk_spoof
                                    )
                                ),
                            )

                            successes += 1

                        except Exception as exc:
                            failures += 1

                            add_activity(
                                "SELECTED THRESHOLD START ERROR",
                                {
                                    "scenario": scenario,
                                    "error": str(exc),
                                },
                            )

                    if successes:
                        st.success(
                            f"Started {successes} threshold scenario(s)."
                        )

                    if failures:
                        st.error(
                            f"{failures} threshold scenario(s) failed."
                        )

                    st.rerun()

        with bulk_col2:
            if selected_thresholds:
                if st.button(
                    "Stop selected thresholds",
                    key="stop_selected_thresholds",
                    use_container_width=True,
                ):
                    stopped = 0
                    failures = 0

                    for scenario in selected_thresholds:
                        try:
                            running = (
                                get_running_threshold(
                                    api,
                                    scenario,
                                )
                            )

                            if not running:
                                continue

                            stop_threshold(
                                api,
                                scenario=scenario,
                                source_id=running[
                                    "source_id"
                                ],
                            )

                            stopped += 1

                        except Exception as exc:
                            failures += 1

                            add_activity(
                                "SELECTED THRESHOLD STOP ERROR",
                                {
                                    "scenario": scenario,
                                    "error": str(exc),
                                },
                            )

                    if stopped:
                        st.success(
                            f"Stopped {stopped} threshold scenario(s)."
                        )

                    if failures:
                        st.error(
                            f"{failures} threshold scenario(s) failed."
                        )

                    st.rerun()

        with bulk_col3:
            if selected_one_shots:
                if st.button(
                    "Launch selected one-shot alerts",
                    type="primary",
                    key="launch_selected_one_shots",
                    use_container_width=True,
                ):
                    successes = 0
                    failures = 0

                    for scenario in selected_one_shots:
                        safe = safe_scenario_key(
                            scenario
                        )

                        try:
                            spoof_value = (
                                st.session_state[
                                    f"selected_alert_spoof_{safe}"
                                ]
                            )

                            result = api.inject_alert(
                                scenario=scenario,
                                patient_id=patient_id,
                                encounter_id=encounter_id,
                                device_id=device_id,
                                spoof_timestamp=(
                                    datetime_to_iso(
                                        spoof_value
                                    )
                                ),
                            )

                            set_alert_status(
                                scenario,
                                result.get(
                                    "status",
                                    "SUBMITTED",
                                ),
                            )

                            add_activity(
                                "SELECTED ONE-SHOT BATCH",
                                result,
                            )

                            successes += 1

                        except Exception as exc:
                            failures += 1

                            add_activity(
                                "SELECTED ONE-SHOT ERROR",
                                {
                                    "scenario": scenario,
                                    "error": str(exc),
                                },
                            )

                    if successes:
                        st.success(
                            f"Launched {successes} one-shot alert(s)."
                        )

                    if failures:
                        st.error(
                            f"{failures} one-shot alert(s) failed."
                        )


# ============================================================================
# ALL ALERTS
# ============================================================================

st.divider()
st.header("All Alerts")

if scenarios:
    st.caption(
        f"{len(scenarios)} scenarios available."
    )

    # ------------------------------------------------------------
    # All threshold controls.
    # ------------------------------------------------------------

    all_threshold_spoof = st.datetime_input(
        "Spoof timestamp for all thresholds",
        value=datetime.now(),
        key="all_threshold_spoof",
        step=DATETIME_INPUT_STEP,
        format="YYYY/MM/DD",
    )

    all_threshold_interval = st.number_input(
        "Interval for all thresholds (seconds)",
        min_value=0.1,
        max_value=3600.0,
        value=1.0,
        step=0.1,
        key="all_threshold_interval",
    )

    threshold_col1, threshold_col2 = st.columns(2)

    with threshold_col1:
        if st.button(
            "Start all threshold alerts",
            type="primary",
            key="start_all_thresholds",
            use_container_width=True,
        ):
            successes = 0
            failures = 0

            for scenario in catalog.get(
                "threshold",
                [],
            ):
                try:
                    if get_running_threshold(
                        api,
                        scenario,
                    ):
                        continue

                    start_threshold(
                        api,
                        scenario=scenario,
                        patient_id=patient_id,
                        encounter_id=encounter_id,
                        device_id=device_id,
                        interval_seconds=(
                            all_threshold_interval
                        ),
                        spoof_timestamp=(
                            datetime_to_iso(
                                all_threshold_spoof
                            )
                        ),
                    )

                    successes += 1

                except Exception as exc:
                    failures += 1

                    add_activity(
                        "ALL THRESHOLD START ERROR",
                        {
                            "scenario": scenario,
                            "error": str(exc),
                        },
                    )

            if successes:
                st.success(
                    f"Started {successes} threshold scenario(s)."
                )

            if failures:
                st.error(
                    f"{failures} threshold scenario(s) failed."
                )

            st.rerun()

    with threshold_col2:
        if st.button(
            "Stop all threshold alerts",
            key="stop_all_thresholds",
            use_container_width=True,
        ):
            stopped, failed = stop_all_thresholds(
                api
            )

            if stopped:
                st.success(
                    f"Stopped {stopped} threshold scenario(s)."
                )

            if failed:
                st.error(
                    f"{failed} threshold scenario(s) failed."
                )

            st.rerun()

    # ------------------------------------------------------------
    # One-shot timestamp preparation.
    # ------------------------------------------------------------

    if st.button(
        "Prepare all one-shot spoof timestamps",
        key="prepare_all_alerts",
        use_container_width=True,
    ):
        now = datetime.now()

        one_shot_scenarios = [
            scenario
            for scenario in scenarios
            if scenario_category(
                scenario,
                catalog,
            ) != "threshold"
        ]

        for index, scenario in enumerate(
            one_shot_scenarios
        ):
            safe = safe_scenario_key(
                scenario
            )

            st.session_state[
                f"all_alert_spoof_{safe}"
            ] = (
                now
                + timedelta(minutes=index)
            )

            st.session_state[
                f"alert_status_{safe}"
            ] = "READY"

        st.success(
            f"Prepared timestamps for "
            f"{len(one_shot_scenarios)} one-shot alerts."
        )

        st.rerun()

    # ------------------------------------------------------------
    # Individual alerts.
    # ------------------------------------------------------------

    for category in (
        "seed",
        "threshold",
        "trend",
    ):
        category_scenarios = catalog.get(
            category,
            [],
        )

        if not category_scenarios:
            continue

        with st.expander(
            f"{category.title()} alerts "
            f"({len(category_scenarios)})",
            expanded=False,
        ):
            for scenario in category_scenarios:
                safe = safe_scenario_key(
                    scenario
                )

                if category == "threshold":
                    col1, col2, col3 = st.columns(
                        [2.2, 2.5, 1.3]
                    )

                    with col1:
                        st.write(
                            f"**{scenario}**"
                        )

                        st.caption(
                            "THRESHOLD · CONTINUOUS"
                        )

                        st.caption(
                            alert_status(scenario)
                        )

                    with col2:
                        threshold_spoof = (
                            st.datetime_input(
                                "Spoof",
                                key=(
                                    f"all_individual_threshold_spoof_{safe}"
                                ),
                                step=DATETIME_INPUT_STEP,
                                format="YYYY/MM/DD",
                            )
                        )

                    with col3:
                        render_threshold_controls(
                            api,
                            scenario=scenario,
                            patient_id=patient_id,
                            encounter_id=encounter_id,
                            device_id=device_id,
                            interval_seconds=(
                                all_threshold_interval
                            ),
                            spoof_timestamp=(
                                datetime_to_iso(
                                    threshold_spoof
                                )
                            ),
                            button_prefix="all_individual_threshold",
                            compact=True,
                        )

                else:
                    col1, col2, col3 = st.columns(
                        [2.2, 3, 1.2]
                    )

                    with col1:
                        st.write(
                            f"**{scenario}**"
                        )

                        st.caption(
                            category.upper()
                        )

                        st.caption(
                            alert_status(scenario)
                        )

                    with col2:
                        st.datetime_input(
                            "Spoof timestamp",
                            key=(
                                f"all_alert_spoof_{safe}"
                            ),
                            step=DATETIME_INPUT_STEP,
                            format="YYYY/MM/DD",
                        )

                    with col3:
                        if st.button(
                            "Launch",
                            key=f"launch_all_single_{safe}",
                            use_container_width=True,
                        ):
                            try:
                                spoof_value = (
                                    st.session_state[
                                        f"all_alert_spoof_{safe}"
                                    ]
                                )

                                result = api.inject_alert(
                                    scenario=scenario,
                                    patient_id=patient_id,
                                    encounter_id=encounter_id,
                                    device_id=device_id,
                                    spoof_timestamp=(
                                        datetime_to_iso(
                                            spoof_value
                                        )
                                    ),
                                )

                                set_alert_status(
                                    scenario,
                                    result.get(
                                        "status",
                                        "SUBMITTED",
                                    ),
                                )

                                add_activity(
                                    "ALL ALERTS / INDIVIDUAL",
                                    result,
                                )

                                st.success(
                                    f"{scenario}: "
                                    f"{result.get('status', 'SUBMITTED')}"
                                )

                            except Exception as exc:
                                show_error(exc)

    # ------------------------------------------------------------
    # Launch all one-shot alerts.
    # ------------------------------------------------------------

    one_shot_scenarios = [
        scenario
        for scenario in scenarios
        if scenario_category(
            scenario,
            catalog,
        ) != "threshold"
    ]

    if one_shot_scenarios:
        if st.button(
            f"Launch all {len(one_shot_scenarios)} one-shot alerts",
            type="primary",
            key="launch_all_alerts",
            use_container_width=True,
        ):
            successes = 0
            failures = 0

            progress = st.progress(0.0)

            for index, scenario in enumerate(
                one_shot_scenarios
            ):
                safe = safe_scenario_key(
                    scenario
                )

                try:
                    spoof_value = (
                        st.session_state[
                            f"all_alert_spoof_{safe}"
                        ]
                    )

                    result = api.inject_alert(
                        scenario=scenario,
                        patient_id=patient_id,
                        encounter_id=encounter_id,
                        device_id=device_id,
                        spoof_timestamp=(
                            datetime_to_iso(
                                spoof_value
                            )
                        ),
                    )

                    set_alert_status(
                        scenario,
                        result.get(
                            "status",
                            "SUBMITTED",
                        ),
                    )

                    add_activity(
                        "ALL ALERTS BATCH",
                        result,
                    )

                    successes += 1

                except Exception as exc:
                    failures += 1

                    add_activity(
                        "ALL ALERTS ERROR",
                        {
                            "scenario": scenario,
                            "error": str(exc),
                        },
                    )

                progress.progress(
                    (index + 1)
                    / len(one_shot_scenarios)
                )

            if successes:
                st.success(
                    f"Launched {successes}/"
                    f"{len(one_shot_scenarios)} "
                    "one-shot alerts."
                )

            if failures:
                st.error(
                    f"{failures} alert(s) failed."
                )


# ============================================================================
# Recent Activity
# ============================================================================

st.divider()
st.header("Recent Activity")

if not st.session_state.recent_activity:
    st.info(
        "No activity yet."
    )

else:
    for activity in (
        st.session_state.recent_activity[:25]
    ):
        with st.container(border=True):
            st.caption(
                f"{activity['time']} · "
                f"{activity['kind']}"
            )

            result = activity["result"]

            if isinstance(result, dict):
                summary_keys = {
                    "injection_id",
                    "source_id",
                    "scenario",
                    "scenario_type",
                    "status",
                    "spoof_timestamp",
                    "injected_at",
                    "message",
                }

                summary = {
                    key: value
                    for key, value in result.items()
                    if key in summary_keys
                }

                st.json(
                    summary
                    if summary
                    else result
                )

            else:
                st.write(result)