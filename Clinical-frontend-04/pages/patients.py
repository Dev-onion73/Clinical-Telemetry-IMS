import streamlit as st


st.title("Patients")
st.caption("Patient registration and clinical identity management")


left, right = st.columns([1, 2])


with left:
    st.subheader("Register Patient")

    with st.form("patient_registration_form"):

        patient_id = st.text_input(
            "Patient ID",
            placeholder="PAT-0001",
        )

        first_name = st.text_input(
            "First name",
        )

        last_name = st.text_input(
            "Last name",
        )

        date_of_birth = st.date_input(
            "Date of birth",
        )

        sex = st.selectbox(
            "Sex",
            [
                "Male",
                "Female",
                "Other",
            ],
        )

        blood_group = st.selectbox(
            "Blood group",
            [
                "A+",
                "A-",
                "B+",
                "B-",
                "AB+",
                "AB-",
                "O+",
                "O-",
            ],
        )

        submitted = st.form_submit_button(
            "Register Patient",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            st.info(
                "Patient API is not connected yet."
            )


with right:
    st.subheader("Patients")

    st.info(
        "Registered patients will appear here."
    )