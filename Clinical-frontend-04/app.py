import streamlit as st


st.set_page_config(
    page_title="Clinical Operations",
    page_icon=":material/local_hospital:",
    layout="wide",
)


st.title("Clinical Operations")
st.caption("Healthcare Incident Management")


pg = st.navigation(
    {
        "Clinical": [
            st.Page(
                "pages/patients.py",
                title="Patients",
                icon=":material/personal_injury:",
                default=True,
            ),
        ],
    }
)

pg.run()