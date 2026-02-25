from datetime import datetime, timedelta

import streamlit as st

from database import (
    create_habit_for_user,
    get_habits_for_user,
    get_done_habit_ids_for_today,
    get_users,
    init_db,
    mark_done_today,
)
from scheduler import run_reminder_check


QUICK_TIME_OPTIONS = [
    "Custom",
    "In 1 hour",
    "In 3 hours",
    "In 12 hours",
    "Morning (09:00)",
    "Lunch (13:00)",
    "Evening (19:00)",
    "Night (22:30)",
]


def get_preset_hhmm(option: str) -> str | None:
    now = datetime.now()
    if option == "In 1 hour":
        return (now + timedelta(hours=1)).strftime("%H:%M")
    if option == "In 3 hours":
        return (now + timedelta(hours=3)).strftime("%H:%M")
    if option == "In 12 hours":
        return (now + timedelta(hours=12)).strftime("%H:%M")

    fixed_times = {
        "Morning (09:00)": "09:00",
        "Lunch (13:00)": "13:00",
        "Evening (19:00)": "19:00",
        "Night (22:30)": "22:30",
    }
    return fixed_times.get(option)

init_db()

current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
last_check_minute = st.session_state.get("last_check_minute")

if last_check_minute != current_minute:
    try:
        run_reminder_check()
        st.session_state.pop("auto_check_warning", None)
    except Exception as exc:
        st.session_state["auto_check_warning"] = str(exc)
    finally:
        st.session_state["last_check_minute"] = current_minute

st.title("Habit Tracker MVP")

st.sidebar.title("User")
users = get_users()
st.sidebar.caption("If your name is not here, send /start to the bot first.")

if users:
    saved_user_labels = [f"{user['name'] or 'Unnamed'} ({user['chat_id']})" for user in users]
    selected_user_label = st.sidebar.selectbox("Registered users", saved_user_labels)
    selected_user = users[saved_user_labels.index(selected_user_label)]
    st.session_state.current_user_id = selected_user["id"]
else:
    selected_user = None
    st.session_state.pop("current_user_id", None)
    st.sidebar.info("No registered users yet.")

current_user_id = st.session_state.get("current_user_id")
if current_user_id is not None:
    st.sidebar.caption(f"Current user id: {current_user_id}")

st.sidebar.title("Debug")
if st.session_state.get("auto_check_warning"):
    st.sidebar.caption("Auto reminder check warning")
    st.sidebar.warning(st.session_state["auto_check_warning"])

simulated_time = st.sidebar.text_input("Simulate time (HH:MM)", placeholder="21:37")

if st.sidebar.button("Run reminder check now"):
    try:
        stripped_time = simulated_time.strip()
        if stripped_time:
            sent_count = run_reminder_check(now_hhmm=stripped_time)
        else:
            sent_count = run_reminder_check()
        st.sidebar.success(f"Sent {sent_count} reminders")
    except ValueError:
        st.sidebar.error("Please enter time in HH:MM format, for example 21:37.")

st.subheader("Create habit")
with st.form("create_habit_form"):
    if "quick_time" not in st.session_state:
        st.session_state.quick_time = QUICK_TIME_OPTIONS[0]
    if "reminder_hh" not in st.session_state:
        st.session_state.reminder_hh = datetime.now().strftime("%H")
    if "reminder_mm" not in st.session_state:
        st.session_state.reminder_mm = datetime.now().strftime("%M")

    name = st.text_input("Habit name")
    quick_time = st.selectbox("Quick time", QUICK_TIME_OPTIONS, key="quick_time")

    preset_hhmm = get_preset_hhmm(quick_time)
    if preset_hhmm is not None:
        preset_hh, preset_mm = preset_hhmm.split(":")
        st.session_state.reminder_hh = preset_hh
        st.session_state.reminder_mm = preset_mm

    hh_col, colon_col, mm_col = st.columns([1, 0.2, 1])
    with hh_col:
        hh_input = st.text_input("HH", key="reminder_hh", placeholder="21")
    with colon_col:
        st.markdown("<div style='text-align:center; padding-top: 30px;'>:</div>", unsafe_allow_html=True)
    with mm_col:
        mm_input = st.text_input("MM", key="reminder_mm", placeholder="37")

    hh_digits = "".join(ch for ch in hh_input if ch.isdigit())[:2]
    mm_digits = "".join(ch for ch in mm_input if ch.isdigit())[:2]

    if hh_digits != hh_input:
        st.session_state.reminder_hh = hh_digits
    if mm_digits != mm_input:
        st.session_state.reminder_mm = mm_digits

    submitted = st.form_submit_button("Add")

if submitted:
    cleaned_name = name.strip()
    hh_raw = st.session_state.get("reminder_hh", "")
    mm_raw = st.session_state.get("reminder_mm", "")
    if current_user_id is None:
        st.error("Please save/select a user in the sidebar first.")
    elif not cleaned_name:
        st.error("Habit name cannot be empty.")
    elif not hh_raw.isdigit() or not mm_raw.isdigit() or not (1 <= len(hh_raw) <= 2) or not (1 <= len(mm_raw) <= 2):
        st.error("Reminder time must be numeric in HH and MM fields.")
    else:
        hh_int = int(hh_raw)
        mm_int = int(mm_raw)
        if not (0 <= hh_int <= 23 and 0 <= mm_int <= 59):
            st.error("Reminder time must be valid (hours 00-23 and minutes 00-59).")
        else:
            hhmm = f"{hh_int:02d}:{mm_int:02d}"
            create_habit_for_user(current_user_id, cleaned_name, hhmm)
            st.success("Habit added!")
            st.rerun()

st.subheader("Your habits")
done_habit_ids = get_done_habit_ids_for_today()
habits = get_habits_for_user(current_user_id) if current_user_id is not None else []

if current_user_id is None:
    st.write("Select or save a user in the sidebar to see habits.")
elif not habits:
    st.write("No habits yet.")
else:
    for habit in habits:
        habit_id = habit["id"]
        is_done_today = habit_id in done_habit_ids

        left_col, right_col = st.columns([4, 1])
        with left_col:
            status = "✅ done today" if is_done_today else "⏳ not done"
            st.write(f"{habit['name']} — {habit['reminder_time']} ({status})")
        with right_col:
            if st.button(
                "Done today",
                key=f"done_{habit_id}",
                disabled=is_done_today,
            ):
                mark_done_today(habit_id)
                st.rerun()