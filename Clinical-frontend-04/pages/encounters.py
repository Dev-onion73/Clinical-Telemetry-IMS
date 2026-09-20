from datetime import datetime, timezone

import streamlit as st

from api.client import (
    MiddlewareError,
    close_encounter,
    close_episode,
    create_fixed_journal_activity,
    create_journal_event,
    end_ongoing_journal_activity,
    get_encounter,
    get_episode,
    start_encounter,
    start_episode_from_journal,
    start_ongoing_journal_activity,
)

from mappings.encounter import (
    CARE_SETTING_OPTIONS,
    ENCOUNTER_TYPE_OPTIONS,
)

from mappings.episode import (
    EPISODE_INITIATION_REASONS,
    EPISODE_ROLE_OPTIONS,
)

from mappings.journal import (
    STAFF_ROLE_OPTIONS,
)


st.title("Encounters")
st.caption(
    "Clinical encounter workspace"
)


# =========================================================
# HELPERS
# =========================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def add_timeline_item(
    item: dict,
):
    if "encounter_timeline" not in st.session_state:
        st.session_state[
            "encounter_timeline"
        ] = []

    st.session_state[
        "encounter_timeline"
    ].append(item)


def clear_encounter_session():
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


# =========================================================
# CURRENT USER
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
staff_id = current_user["staff_id"]


# =========================================================
# PATIENT CONTEXT
# =========================================================

patient = st.session_state.get(
    "selected_patient"
)

if patient is None:

    st.warning(
        "Select a patient from the Patients page first."
    )

    st.page_link(
        "pages/patients.py",
        label="Go to Patients",
        icon=":material/personal_injury:",
    )

    st.stop()


patient_id = patient.get(
    "patient_id"
)

first_name = patient.get(
    "first_name",
    "",
)

last_name = patient.get(
    "last_name",
    "",
)

patient_name = (
    f"{first_name} {last_name}"
).strip()


# =========================================================
# PATIENT HEADER
# =========================================================

with st.container(border=True):

    patient_col, action_col = st.columns(
        [4, 1]
    )

    with patient_col:

        st.subheader(
            patient_name or "Patient"
        )

        st.caption(
            f"Patient ID: {patient_id}"
        )

    with action_col:

        st.write("")

        if st.button(
            "Change patient",
            use_container_width=True,
        ):

            st.session_state[
                "selected_patient"
            ] = None

            clear_encounter_session()

            st.switch_page(
                "pages/patients.py"
            )


# =========================================================
# OPEN ENCOUNTER
# =========================================================

st.divider()

st.subheader("Open Encounter")

with st.form(
    "encounter_lookup_form"
):

    encounter_lookup_id = st.text_input(
        "Encounter ID",
        placeholder="TESTE100",
    )

    lookup_submitted = (
        st.form_submit_button(
            "Open Encounter",
            type="primary",
            use_container_width=True,
        )
    )


if lookup_submitted:

    if not encounter_lookup_id.strip():

        st.error(
            "Encounter ID is required."
        )

    else:

        try:

            encounter = get_encounter(
                encounter_lookup_id.strip()
            )

            st.session_state[
                "selected_encounter"
            ] = encounter

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
                "Encounter loaded."
            )

            st.rerun()

        except MiddlewareError as exc:

            st.error(str(exc))


# =========================================================
# START ENCOUNTER
# =========================================================

st.divider()

st.subheader("Start Encounter")

with st.form(
    "start_encounter_form"
):

    col1, col2 = st.columns(2)

    with col1:

        encounter_id = st.text_input(
            "Encounter ID",
            placeholder="TESTE100",
        )

        encounter_type_label = (
            st.selectbox(
                "Encounter type",
                list(
                    ENCOUNTER_TYPE_OPTIONS.keys()
                ),
            )
        )

        care_setting_label = (
            st.selectbox(
                "Care setting",
                list(
                    CARE_SETTING_OPTIONS.keys()
                ),
            )
        )

    with col2:

        start_reason = st.text_input(
            "Start reason",
            placeholder=(
                "Acute clinical evaluation"
            ),
        )

        start_details = st.text_area(
            "Start details",
            placeholder=(
                "Additional encounter context."
            ),
        )

    start_submitted = (
        st.form_submit_button(
            "Start Encounter",
            type="primary",
            use_container_width=True,
        )
    )


if start_submitted:

    if not encounter_id.strip():

        st.error(
            "Encounter ID is required."
        )

    elif not start_reason.strip():

        st.error(
            "Start reason is required."
        )

    else:

        payload = {
            "encounter_id": encounter_id.strip(),
            "patient_id": patient_id,
            "encounter_type": (
                ENCOUNTER_TYPE_OPTIONS[
                    encounter_type_label
                ]
            ),
            "care_setting": (
                CARE_SETTING_OPTIONS[
                    care_setting_label
                ]
            ),
            "start_reason": start_reason.strip(),
            "started_by": staff_id,
            "started_by_role": current_role,
            "start_details": (
                start_details.strip()
                or None
            ),
            "start_time": utc_now(),
        }

        try:

            encounter = start_encounter(
                payload
            )

            st.session_state[
                "selected_encounter"
            ] = encounter

            st.session_state[
                "last_episode"
            ] = None

            st.session_state[
                "last_ongoing_activity"
            ] = None

            st.session_state[
                "encounter_timeline"
            ] = []

            add_timeline_item(
                {
                    "kind": "encounter",
                    "label": "Encounter started",
                    "data": encounter,
                }
            )

            st.success(
                "Encounter started."
            )

            st.rerun()

        except MiddlewareError as exc:

            st.error(str(exc))


# =========================================================
# SELECTED ENCOUNTER
# =========================================================

encounter = st.session_state.get(
    "selected_encounter"
)

if encounter is None:

    st.info(
        "Open an existing encounter or start a new one."
    )

    st.stop()


encounter_id = encounter.get(
    "encounter_id"
)

encounter_status = encounter.get(
    "status",
    "UNKNOWN",
)


# =========================================================
# ENCOUNTER SUMMARY
# =========================================================

st.divider()

st.subheader(
    f"Encounter {encounter_id}"
)

status_col, type_col, setting_col = (
    st.columns(3)
)

with status_col:

    if encounter_status == "CLOSED":

        st.success(
            f"Status: {encounter_status}"
        )

    else:

        st.info(
            f"Status: {encounter_status}"
        )


with type_col:

    st.metric(
        "Encounter type",
        encounter.get(
            "encounter_type",
            "—",
        ),
    )


with setting_col:

    st.metric(
        "Care setting",
        encounter.get(
            "care_setting",
            "—",
        ),
    )


with st.expander(
    "Encounter data",
    expanded=False,
):

    st.json(encounter)


# =========================================================
# EPISODES
# =========================================================

st.divider()

st.subheader("Episodes")

episode_start_col, episode_lookup_col = (
    st.columns(2)
)


# ---------------------------------------------------------
# START EPISODE
# ---------------------------------------------------------

with episode_start_col:

    st.markdown(
        "### Start Episode"
    )

    with st.form(
        "start_episode_form"
    ):

        episode_id = st.text_input(
            "Episode ID",
            placeholder="TESTE100_EP01",
        )

        journal_id = st.text_input(
            "Journal ID",
            placeholder="J-EVENT-100",
        )

        initiated_by = st.text_input(
            "Initiated by",
            value=staff_id,
        )

        episode_role_label = (
            st.selectbox(
                "Author role",
                list(
                    EPISODE_ROLE_OPTIONS.keys()
                ),
            )
        )

        initiation_reason = (
            st.selectbox(
                "Initiation reason",
                EPISODE_INITIATION_REASONS,
            )
        )

        content = st.text_area(
            "Clinical content",
            placeholder=(
                "Why this episode was initiated."
            ),
        )

        episode_start_time = st.text_input(
            "Start time",
            value=utc_now(),
        )

        episode_submitted = (
            st.form_submit_button(
                "Start Episode",
                type="primary",
                use_container_width=True,
            )
        )


    if episode_submitted:

        if not episode_id.strip():

            st.error(
                "Episode ID is required."
            )

        elif not journal_id.strip():

            st.error(
                "Journal ID is required."
            )

        elif not content.strip():

            st.error(
                "Clinical content is required."
            )

        else:

            payload = {
                "episode_id": (
                    episode_id.strip()
                ),
                "journal_id": (
                    journal_id.strip()
                ),
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "initiated_by": (
                    initiated_by.strip()
                ),
                "initiation_reason": (
                    initiation_reason
                ),
                "author_role": (
                    EPISODE_ROLE_OPTIONS[
                        episode_role_label
                    ]
                ),
                "content": content.strip(),
                "start_time": (
                    episode_start_time.strip()
                ),
            }

            try:

                episode = (
                    start_episode_from_journal(
                        payload
                    )
                )

                st.session_state[
                    "last_episode"
                ] = episode

                add_timeline_item(
                    {
                        "kind": "episode",
                        "label": "Episode started",
                        "data": episode,
                    }
                )

                st.success(
                    "Episode started."
                )

                st.rerun()

            except MiddlewareError as exc:

                st.error(str(exc))


# ---------------------------------------------------------
# LOAD EPISODE
# ---------------------------------------------------------

with episode_lookup_col:

    st.markdown(
        "### Load Episode"
    )

    with st.form(
        "episode_lookup_form"
    ):

        episode_lookup_id = st.text_input(
            "Episode ID",
            placeholder="TESTE100_EP01",
        )

        episode_lookup_submitted = (
            st.form_submit_button(
                "Load Episode",
                use_container_width=True,
            )
        )


    if episode_lookup_submitted:

        if not episode_lookup_id.strip():

            st.error(
                "Episode ID is required."
            )

        else:

            try:

                episode = get_episode(
                    episode_lookup_id.strip()
                )

                st.session_state[
                    "last_episode"
                ] = episode

                st.success(
                    "Episode loaded."
                )

            except MiddlewareError as exc:

                st.error(str(exc))


# =========================================================
# CURRENT EPISODE
# =========================================================

episode = st.session_state.get(
    "last_episode"
)

if episode:

    with st.expander(
        "Current episode",
        expanded=True,
    ):

        st.json(episode)

        episode_id = episode.get(
            "episode_id"
        )

        episode_status = episode.get(
            "status",
            "UNKNOWN",
        )

        if episode_status != "CLOSED":

            with st.form(
                "close_episode_form"
            ):

                close_episode_submitted = (
                    st.form_submit_button(
                        "Close Episode",
                        type="primary",
                        use_container_width=True,
                    )
                )


            if close_episode_submitted:

                payload = {
                    "closure_by": staff_id,
                    "end_time": utc_now(),
                }

                try:

                    closed_episode = (
                        close_episode(
                            episode_id,
                            payload,
                        )
                    )

                    st.session_state[
                        "last_episode"
                    ] = closed_episode

                    add_timeline_item(
                        {
                            "kind": "episode_end",
                            "label": "Episode closed",
                            "data": closed_episode,
                        }
                    )

                    st.success(
                        "Episode closed."
                    )

                    st.rerun()

                except MiddlewareError as exc:

                    st.error(str(exc))

        else:

            st.success(
                "This episode is closed."
            )


# =========================================================
# JOURNAL EVENT
# =========================================================

st.divider()

st.subheader("Journal Event")

with st.form(
    "journal_event_form"
):

    journal_event_id = st.text_input(
        "Journal ID",
        placeholder="J-EVENT-101",
    )

    event_role_label = (
        st.selectbox(
            "Staff role",
            list(
                STAFF_ROLE_OPTIONS.keys()
            ),
        )
    )

    event_content = st.text_area(
        "Clinical observation",
        placeholder=(
            "Describe the point-in-time observation."
        ),
    )

    event_timestamp = st.text_input(
        "Timestamp",
        value=utc_now(),
    )

    event_episode_id = st.text_input(
        "Episode ID (optional)",
        placeholder="TESTE100_EP01",
    )

    event_submitted = (
        st.form_submit_button(
            "Create Journal Event",
            type="primary",
            use_container_width=True,
        )
    )


if event_submitted:

    if not journal_event_id.strip():

        st.error(
            "Journal ID is required."
        )

    elif not event_content.strip():

        st.error(
            "Clinical observation is required."
        )

    else:

        payload = {
            "journal_id": (
                journal_event_id.strip()
            ),
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "author_id": staff_id,
            "author_role": (
                STAFF_ROLE_OPTIONS[
                    event_role_label
                ]
            ),
            "content": (
                event_content.strip()
            ),
            "timestamp": (
                event_timestamp.strip()
            ),
            "episode_id": (
                event_episode_id.strip()
                or None
            ),
        }

        try:

            journal = create_journal_event(
                payload
            )

            add_timeline_item(
                {
                    "kind": "journal_event",
                    "label": "Journal event",
                    "data": journal,
                }
            )

            st.success(
                "Journal event created."
            )

            st.rerun()

        except MiddlewareError as exc:

            st.error(str(exc))


# =========================================================
# FIXED JOURNAL ACTIVITY
# =========================================================

st.divider()

st.subheader(
    "Fixed Journal Activity"
)

with st.form(
    "fixed_activity_form"
):

    fixed_journal_id = st.text_input(
        "Journal ID",
        placeholder="J-ACT-101",
    )

    fixed_role_label = (
        st.selectbox(
            "Staff role",
            list(
                STAFF_ROLE_OPTIONS.keys()
            ),
            key="fixed_role",
        )
    )

    fixed_content = st.text_area(
        "Activity",
        placeholder=(
            "Describe the completed clinical activity."
        ),
    )

    fixed_start_time = st.text_input(
        "Start time",
        value=utc_now(),
    )

    fixed_end_time = st.text_input(
        "End time",
        value=utc_now(),
    )

    fixed_start_reason = st.text_input(
        "Start reason",
        placeholder="Procedure initiated",
    )

    fixed_end_reason = st.text_input(
        "End reason",
        placeholder="Procedure completed",
    )

    fixed_episode_id = st.text_input(
        "Episode ID (optional)",
        placeholder="TESTE100_EP01",
        key="fixed_episode_id",
    )

    fixed_submitted = (
        st.form_submit_button(
            "Create Fixed Activity",
            type="primary",
            use_container_width=True,
        )
    )


if fixed_submitted:

    if not fixed_journal_id.strip():

        st.error(
            "Journal ID is required."
        )

    elif not fixed_content.strip():

        st.error(
            "Activity content is required."
        )

    elif not fixed_start_reason.strip():

        st.error(
            "Start reason is required."
        )

    elif not fixed_end_reason.strip():

        st.error(
            "End reason is required."
        )

    else:

        payload = {
            "journal_id": (
                fixed_journal_id.strip()
            ),
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "author_id": staff_id,
            "author_role": (
                STAFF_ROLE_OPTIONS[
                    fixed_role_label
                ]
            ),
            "content": fixed_content.strip(),
            "start_time": (
                fixed_start_time.strip()
            ),
            "end_time": (
                fixed_end_time.strip()
            ),
            "start_reason": (
                fixed_start_reason.strip()
            ),
            "end_reason": (
                fixed_end_reason.strip()
            ),
            "episode_id": (
                fixed_episode_id.strip()
                or None
            ),
        }

        try:

            journal = (
                create_fixed_journal_activity(
                    payload
                )
            )

            add_timeline_item(
                {
                    "kind": "journal_activity",
                    "label": (
                        "Fixed journal activity"
                    ),
                    "data": journal,
                }
            )

            st.success(
                "Fixed journal activity created."
            )

            st.rerun()

        except MiddlewareError as exc:

            st.error(str(exc))


# =========================================================
# ONGOING JOURNAL ACTIVITY
# =========================================================

st.divider()

st.subheader(
    "Ongoing Journal Activity"
)

with st.form(
    "ongoing_activity_start_form"
):

    ongoing_journal_id = st.text_input(
        "Journal ID",
        placeholder="J-ACT-102",
    )

    ongoing_role_label = (
        st.selectbox(
            "Staff role",
            list(
                STAFF_ROLE_OPTIONS.keys()
            ),
            key="ongoing_role",
        )
    )

    ongoing_content = st.text_area(
        "Activity",
        placeholder=(
            "Describe the activity that will remain active."
        ),
    )

    ongoing_start_time = st.text_input(
        "Start time",
        value=utc_now(),
    )

    ongoing_start_reason = st.text_input(
        "Start reason",
        placeholder="Observation initiated",
    )

    ongoing_episode_id = st.text_input(
        "Episode ID (optional)",
        placeholder="TESTE100_EP01",
        key="ongoing_episode_id",
    )

    ongoing_start_submitted = (
        st.form_submit_button(
            "Start Ongoing Activity",
            type="primary",
            use_container_width=True,
        )
    )


if ongoing_start_submitted:

    if not ongoing_journal_id.strip():

        st.error(
            "Journal ID is required."
        )

    elif not ongoing_content.strip():

        st.error(
            "Activity content is required."
        )

    elif not ongoing_start_reason.strip():

        st.error(
            "Start reason is required."
        )

    else:

        payload = {
            "journal_id": (
                ongoing_journal_id.strip()
            ),
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "author_id": staff_id,
            "author_role": (
                STAFF_ROLE_OPTIONS[
                    ongoing_role_label
                ]
            ),
            "content": (
                ongoing_content.strip()
            ),
            "start_time": (
                ongoing_start_time.strip()
            ),
            "start_reason": (
                ongoing_start_reason.strip()
            ),
            "episode_id": (
                ongoing_episode_id.strip()
                or None
            ),
        }

        try:

            journal = (
                start_ongoing_journal_activity(
                    payload
                )
            )

            st.session_state[
                "last_ongoing_activity"
            ] = journal

            add_timeline_item(
                {
                    "kind": "journal_activity_start",
                    "label": (
                        "Ongoing activity started"
                    ),
                    "data": journal,
                }
            )

            st.success(
                "Ongoing activity started."
            )

            st.rerun()

        except MiddlewareError as exc:

            st.error(str(exc))


# =========================================================
# END ONGOING ACTIVITY
# =========================================================

ongoing_activity = st.session_state.get(
    "last_ongoing_activity"
)

if ongoing_activity:

    st.markdown(
        "### Active Ongoing Activity"
    )

    st.json(
        ongoing_activity
    )

    ongoing_journal_id = (
        ongoing_activity.get(
            "journal_id"
        )
    )

    if ongoing_journal_id:

        with st.form(
            "ongoing_activity_end_form"
        ):

            ongoing_end_time = st.text_input(
                "End time",
                value=utc_now(),
            )

            ongoing_end_reason = st.text_input(
                "End reason",
                placeholder="Activity completed",
            )

            ongoing_end_submitted = (
                st.form_submit_button(
                    "End Ongoing Activity",
                    type="primary",
                    use_container_width=True,
                )
            )


        if ongoing_end_submitted:

            if not ongoing_end_reason.strip():

                st.error(
                    "End reason is required."
                )

            else:

                payload = {
                    "end_time": (
                        ongoing_end_time.strip()
                    ),
                    "end_reason": (
                        ongoing_end_reason.strip()
                    ),
                    "actor_id": staff_id,
                    "actor_role": current_role,
                }

                try:

                    ended_activity = (
                        end_ongoing_journal_activity(
                            ongoing_journal_id,
                            payload,
                        )
                    )

                    add_timeline_item(
                        {
                            "kind": (
                                "journal_activity_end"
                            ),
                            "label": (
                                "Ongoing activity ended"
                            ),
                            "data": ended_activity,
                        }
                    )

                    st.session_state[
                        "last_ongoing_activity"
                    ] = None

                    st.success(
                        "Ongoing activity ended."
                    )

                    st.rerun()

                except MiddlewareError as exc:

                    st.error(str(exc))


# =========================================================
# CLOSE ENCOUNTER
# =========================================================

st.divider()

st.subheader(
    "Dispatch / Close Encounter"
)

if encounter_status != "CLOSED":

    with st.form(
        "close_encounter_form"
    ):

        encounter_end_reason = (
            st.text_input(
                "End reason",
                placeholder=(
                    "Clinical evaluation completed"
                ),
            )
        )

        encounter_end_details = (
            st.text_area(
                "End details",
                placeholder=(
                    "Patient stable and discharged."
                ),
            )
        )

        close_submitted = (
            st.form_submit_button(
                "Dispatch / Close Encounter",
                type="primary",
                use_container_width=True,
            )
        )


    if close_submitted:

        if not encounter_end_reason.strip():

            st.error(
                "End reason is required."
            )

        else:

            payload = {
                "end_reason": (
                    encounter_end_reason.strip()
                ),
                "ended_by": staff_id,
                "actor_role": current_role,
                "end_details": (
                    encounter_end_details.strip()
                    or None
                ),
                "end_time": utc_now(),
            }

            try:

                closed_encounter = (
                    close_encounter(
                        encounter_id,
                        payload,
                    )
                )

                st.session_state[
                    "selected_encounter"
                ] = closed_encounter

                add_timeline_item(
                    {
                        "kind": "encounter_end",
                        "label": "Encounter closed",
                        "data": closed_encounter,
                    }
                )

                st.success(
                    "Encounter closed."
                )

                st.rerun()

            except MiddlewareError as exc:

                st.error(str(exc))

else:

    st.success(
        "This encounter is closed."
    )


# =========================================================
# SESSION TIMELINE
# =========================================================

st.divider()

st.subheader(
    "Clinical Timeline"
)

timeline = st.session_state.get(
    "encounter_timeline",
    [],
)


if not timeline:

    st.info(
        "Clinical activity created during this UI session will appear here."
    )

else:

    for item in reversed(timeline):

        kind = item.get(
            "kind",
            "event",
        )

        label = item.get(
            "label",
            "Clinical event",
        )

        data = item.get(
            "data",
            {},
        )

        if kind == "encounter":
            marker = "Encounter"

        elif kind == "encounter_end":
            marker = "Encounter closed"

        elif kind == "episode":
            marker = "Episode"

        elif kind == "episode_end":
            marker = "Episode closed"

        elif kind == "journal_event":
            marker = "Event"

        elif kind == "journal_activity":
            marker = "Activity"

        elif kind == "journal_activity_start":
            marker = "Activity started"

        elif kind == "journal_activity_end":
            marker = "Activity ended"

        else:
            marker = "Clinical"

        with st.container(
            border=True
        ):

            st.markdown(
                f"**{marker} — {label}**"
            )

            if isinstance(
                data,
                dict,
            ):

                timestamp = (
                    data.get(
                        "timestamp"
                    )
                    or data.get(
                        "start_time"
                    )
                    or data.get(
                        "end_time"
                    )
                )

                if timestamp:

                    st.caption(
                        str(timestamp)
                    )

                st.json(data)

            else:

                st.write(data)