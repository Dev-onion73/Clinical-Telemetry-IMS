import streamlit as st
from datetime import date

from api.client import (
    MiddlewareError,
    register_patient,
)

from mappings.patient import (
    BLOOD_GROUP_OPTIONS,
    SEX_OPTIONS,
)


st.title("Patient Registration")
st.caption(
    "Standalone patient registration"
)


with st.form(
    "standalone_patient_registration_form"
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

    submitted = st.form_submit_button(
        "Register Patient",
        type="primary",
        use_container_width=True,
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

            st.success(
                "Patient registered successfully."
            )

            st.json(patient)

        except MiddlewareError as exc:

            st.error(str(exc))