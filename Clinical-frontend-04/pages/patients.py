from datetime import date

import streamlit as st

from api.client import (
    MiddlewareError,
    get_patient,
    list_patients,
    register_patient,
)

from mappings.patient import (
    BLOOD_GROUP_OPTIONS,
    SEX_OPTIONS,
)


st.title("Patients")
st.caption(
    "Patient identity and clinical access"
)


# =========================================================
# SELECTED PATIENT
# =========================================================

selected_patient = st.session_state.get(
    "selected_patient"
)


if selected_patient:

    first_name = selected_patient.get(
        "first_name",
        "",
    )

    last_name = selected_patient.get(
        "last_name",
        "",
    )

    patient_id = selected_patient.get(
        "patient_id",
        "",
    )

    patient_name = (
        f"{first_name} {last_name}"
    ).strip()

    with st.container(border=True):

        identity_col, action_col = st.columns(
            [4, 1]
        )

        with identity_col:

            st.subheader(
                patient_name or "Patient"
            )

            st.caption(
                f"Patient ID: {patient_id}"
            )

        with action_col:

            st.write("")

            if st.button(
                "Clear",
                use_container_width=True,
            ):

                st.session_state[
                    "selected_patient"
                ] = None

                st.session_state[
                    "selected_encounter"
                ] = None

                st.session_state[
                    "last_episode"
                ] = None

                st.session_state[
                    "last_ongoing_activity"
                ] = None

                st.session_state[
                    "encounter_timeline"
                ] = []

                st.rerun()


# =========================================================
# PATIENT LOOKUP
# =========================================================

st.divider()

st.subheader("Find Patient")

with st.form(
    "patient_lookup_form"
):

    lookup_id = st.text_input(
        "Patient ID",
        placeholder="PAT0003",
    )

    lookup_submitted = (
        st.form_submit_button(
            "Find Patient",
            type="primary",
            use_container_width=True,
        )
    )


if lookup_submitted:

    if not lookup_id.strip():

        st.error(
            "Patient ID is required."
        )

    else:

        try:

            patient = get_patient(
                lookup_id.strip()
            )

            if isinstance(
                patient,
                dict,
            ):

                st.session_state[
                    "selected_patient"
                ] = patient

                st.session_state[
                    "selected_encounter"
                ] = None

                st.session_state[
                    "last_episode"
                ] = None

                st.session_state[
                    "last_ongoing_activity"
                ] = None

                st.session_state[
                    "encounter_timeline"
                ] = []

                st.success(
                    "Patient selected."
                )

                st.rerun()

            else:

                st.error(
                    "Middleware returned an unexpected patient response."
                )

                st.write(patient)

        except MiddlewareError as exc:

            st.error(str(exc))


# =========================================================
# PATIENT REGISTRATION
# =========================================================

st.divider()

register_col, list_col = st.columns(
    [1, 1]
)


with register_col:

    st.subheader("Register Patient")

    with st.form(
        "patient_registration_form"
    ):

        patient_id = st.text_input(
            "Patient ID",
            placeholder="PAT0004",
        )

        first_name = st.text_input(
            "First name",
        )

        last_name = st.text_input(
            "Last name",
        )

        date_of_birth = st.date_input(
            "Date of birth",
            value=date(2000, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )

        sex_label = st.selectbox(
            "Sex",
            list(
                SEX_OPTIONS.keys()
            ),
        )

        blood_group_label = st.selectbox(
            "Blood group",
            list(
                BLOOD_GROUP_OPTIONS.keys()
            ),
        )

        submitted = (
            st.form_submit_button(
                "Register Patient",
                type="primary",
                use_container_width=True,
            )
        )


    if submitted:

        if not patient_id.strip():

            st.error(
                "Patient ID is required."
            )

        elif not first_name.strip():

            st.error(
                "First name is required."
            )

        elif not last_name.strip():

            st.error(
                "Last name is required."
            )

        else:

            payload = {
                "patient_id": patient_id.strip(),
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "date_of_birth": (
                    date_of_birth.isoformat()
                ),
                "sex": SEX_OPTIONS[
                    sex_label
                ],
                "blood_group": (
                    BLOOD_GROUP_OPTIONS[
                        blood_group_label
                    ]
                ),
            }

            try:

                patient = register_patient(
                    payload
                )

                if isinstance(
                    patient,
                    dict,
                ):

                    st.session_state[
                        "selected_patient"
                    ] = patient

                st.success(
                    "Patient registered successfully."
                )

                st.rerun()

            except MiddlewareError as exc:

                st.error(
                    f"Patient registration failed: {exc}"
                )


# =========================================================
# PATIENT LIST
# =========================================================

with list_col:

    st.subheader("Patient List")

    if st.button(
        "Refresh",
        use_container_width=True,
    ):

        try:

            patients = list_patients()

            st.session_state[
                "patient_list"
            ] = patients

        except MiddlewareError as exc:

            st.error(str(exc))


    patients = st.session_state.get(
        "patient_list"
    )


    if patients is None:

        st.info(
            "Click Refresh to load patients."
        )

    elif isinstance(
        patients,
        list,
    ):

        if not patients:

            st.info(
                "No patients found."
            )

        else:

            for index, patient in enumerate(
                patients
            ):

                if not isinstance(
                    patient,
                    dict,
                ):
                    continue

                listed_patient_id = (
                    patient.get(
                        "patient_id",
                        f"patient-{index}",
                    )
                )

                first_name = patient.get(
                    "first_name",
                    "",
                )

                last_name = patient.get(
                    "last_name",
                    "",
                )

                label = (
                    f"{listed_patient_id} — "
                    f"{first_name} "
                    f"{last_name}"
                ).strip()

                if st.button(
                    label,
                    key=(
                        f"select_patient_"
                        f"{listed_patient_id}"
                    ),
                    use_container_width=True,
                ):

                    st.session_state[
                        "selected_patient"
                    ] = patient

                    st.session_state[
                        "selected_encounter"
                    ] = None

                    st.session_state[
                        "last_episode"
                    ] = None

                    st.session_state[
                        "last_ongoing_activity"
                    ] = None

                    st.session_state[
                        "encounter_timeline"
                    ] = []

                    st.rerun()

    else:

        st.warning(
            "Middleware returned an unexpected patient-list response."
        )

        st.json(patients)