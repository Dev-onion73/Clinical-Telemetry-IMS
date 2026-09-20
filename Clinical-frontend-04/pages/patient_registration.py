import streamlit as st

from api.client import register_patient
from mappings.patient import (
    SEX_OPTIONS,
    BLOOD_GROUP_OPTIONS,
)


st.title("Patient Registration")


patient_id = st.text_input("Patient ID")
first_name = st.text_input("First name")
last_name = st.text_input("Last name")
date_of_birth = st.date_input("Date of birth")

sex_label = st.selectbox(
    "Sex",
    list(SEX_OPTIONS.keys()),
)

blood_group_label = st.selectbox(
    "Blood group",
    list(BLOOD_GROUP_OPTIONS.keys()),
)


if st.button("Register patient"):

    payload = {
        "patient_id": patient_id,
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": date_of_birth.isoformat(),
        "sex": SEX_OPTIONS[sex_label],
        "blood_group": BLOOD_GROUP_OPTIONS[blood_group_label],
    }

    try:
        patient = register_patient(payload)

        st.success("Patient registered successfully")
        st.json(patient)

    except Exception as exc:
        st.error(str(exc))