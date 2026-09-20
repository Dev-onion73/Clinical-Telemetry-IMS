from datetime import datetime, timezone

import streamlit as st

from api.client import (
    MiddlewareError,
    close_encounter,
    get_encounter,
    start_encounter,
)
from mappings.encounter import (
    CARE_SETTING_OPTIONS,
    ENCOUNTER_TYPE_OPTIONS,
)


st.title("Encounters")
st.caption("Encounter admission, lifecycle and dispatch")


# =========================================================
# Session identity
# =========================================================

current_user = st.session_state.get(
    "current_user",
    {
        "staff_id": "ADMIN-001",
        "role": "ADMIN",
        "name": "System Administrator",
    },
)

current_role = current_user["role"]


# =========================================================
# START ENCOUNTER
# =========================================================

if current_role == "ADMIN":

    st.subheader("Start Encounter")

    with st.form("start_encounter_form"):

        encounter_id = st.text_input(
            "Encounter ID",
            placeholder="E1",
        )

        patient_id = st.text_input(
            "Patient ID",
            placeholder="PAT-0001",
        )

        encounter_type_label = st.selectbox(
            "Encounter type",
            list(ENCOUNTER_TYPE_OPTIONS.keys()),
        )

        care_setting_label = st.selectbox(
            "Care setting",
            list(CARE_SETTING_OPTIONS.keys()),
        )

        start_reason = st.text_input(
            "Start reason",
            placeholder="Emergency admission",
        )

        start_details = st.text_area(
            "Start details",
            placeholder="Additional encounter context",
        )

        submitted = st.form_submit_button(
            "Start Encounter",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        if not encounter_id.strip():
            st.error("Encounter ID is required.")

        elif not patient_id.strip():
            st.error("Patient ID is required.")

        elif not start_reason.strip():
            st.error("Start reason is required.")

        else:

            payload = {
                "encounter_id": encounter_id.strip(),
                "patient_id": patient_id.strip(),
                "encounter_type": ENCOUNTER_TYPE_OPTIONS[
                    encounter_type_label
                ],
                "care_setting": CARE_SETTING_OPTIONS[
                    care_setting_label
                ],
                "start_reason": start_reason.strip(),
                "started_by": current_user["staff_id"],
                "started_by_role": current_role,
                "start_details": (
                    start_details.strip()
                    or None
                ),
                "start_time": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            try:

                encounter = start_encounter(
                    payload
                )

                st.session_state[
                    "last_encounter"
                ] = encounter

                st.success(
                    "Encounter started successfully."
                )

            except MiddlewareError as exc:

                st.error(str(exc))


else:

    st.info(
        "Encounter creation is restricted to administrators."
    )


# =========================================================
# LAST ENCOUNTER
# =========================================================

st.divider()

st.subheader("Encounter")

last_encounter = st.session_state.get(
    "last_encounter"
)

if last_encounter is None:

    st.info(
        "No encounter has been started during this session."
    )

else:

    st.json(last_encounter)

    encounter_id = last_encounter["encounter_id"]

    st.subheader("Dispatch / Close Encounter")

    if last_encounter.get("status") != "CLOSED":

        if current_role == "ADMIN":

            with st.form(
                "close_encounter_form"
            ):

                end_reason = st.text_input(
                    "End reason",
                    placeholder="Patient discharged",
                )

                end_details = st.text_area(
                    "End details",
                    placeholder="Dispatch / closure details",
                )

                close_submitted = st.form_submit_button(
                    "Dispatch / Close Encounter",
                    type="primary",
                    use_container_width=True,
                )

            if close_submitted:

                if not end_reason.strip():

                    st.error(
                        "End reason is required."
                    )

                else:

                    payload = {
                        "end_reason": end_reason.strip(),
                        "ended_by": current_user[
                            "staff_id"
                        ],
                        "actor_role": current_role,
                        "end_details": (
                            end_details.strip()
                            or None
                        ),
                        "end_time": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }

                    try:

                        encounter = close_encounter(
                            encounter_id,
                            payload,
                        )

                        st.session_state[
                            "last_encounter"
                        ] = encounter

                        st.success(
                            "Encounter dispatched successfully."
                        )

                        st.rerun()

                    except MiddlewareError as exc:

                        st.error(str(exc))

        else:

            st.info(
                "Encounter dispatch is restricted to administrators."
            )

    else:

        st.success(
            "This encounter is closed."
        )