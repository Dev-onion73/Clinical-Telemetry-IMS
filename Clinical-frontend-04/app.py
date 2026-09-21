import streamlit as st


st.set_page_config(
    page_title="Clinical Operations",
    page_icon=":material/local_hospital:",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

if "current_user" not in st.session_state:
    st.session_state["current_user"] = {
        "staff_id": "ADMIN-001",
        "role": "ADMIN",
        "name": "System Administrator",
    }

if "selected_patient" not in st.session_state:
    st.session_state["selected_patient"] = None

if "selected_encounter" not in st.session_state:
    st.session_state["selected_encounter"] = None

if "last_episode" not in st.session_state:
    st.session_state["last_episode"] = None

if "last_ongoing_activity" not in st.session_state:
    st.session_state["last_ongoing_activity"] = None

if "patient_list" not in st.session_state:
    st.session_state["patient_list"] = None

if "encounter_timeline" not in st.session_state:
    st.session_state["encounter_timeline"] = []


# =========================================================
# APPLICATION HEADER
# =========================================================

st.title("Clinical Operations")
st.caption("Healthcare Incident Management")


# =========================================================
# NAVIGATION
# =========================================================

pg = st.navigation(
    {
        "Clinical": [
            st.Page(
                "pages/patients.py",
                title="Patients",
                icon=":material/personal_injury:",
                default=True,
            ),
            st.Page(
                "pages/encounters.py",
                title="Encounters",
                icon=":material/meeting_room:",
            ),
        ],
    }
)


pg.run()