import re
from datetime import datetime, timedelta

import streamlit as st

from database import (
    create_habit_for_user,
    get_habits_for_user,
    get_done_habit_ids_for_today,
    get_users,
    init_db,
    mark_done_today,
    upsert_user,
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


def is_valid_hhmm(value: str) -> bool:
    return bool(re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value.strip()))


def hhmm_to_digits(value: str) -> str:
    return value.replace(":", "")


def digits_to_hhmm(value: str) -> str:
    return f"{value[:2]}:{value[2:4]}"


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

saved_user_labels = [f"{user['name'] or 'Unnamed'} ({user['chat_id']})" for user in users]
selected_user_label = st.sidebar.selectbox(
    "Saved users",
    ["New user"] + saved_user_labels,
)

selected_user = None
if selected_user_label != "New user":
    selected_user = users[saved_user_labels.index(selected_user_label)]

default_name = selected_user["name"] if selected_user else ""
default_chat_id = selected_user["chat_id"] if selected_user else ""

user_name = st.sidebar.text_input("Name", value=default_name)
user_chat_id = st.sidebar.text_input("Chat ID", value=default_chat_id)

if st.sidebar.button("Save user"):
    clean_name = user_name.strip()
    clean_chat_id = user_chat_id.strip()
    if not clean_chat_id:
        st.sidebar.error("Chat ID is required.")
    else:
        current_user_id = upsert_user(clean_name, clean_chat_id)
        st.session_state.current_user_id = current_user_id
        st.sidebar.success(f"User saved (id={current_user_id})")

if "current_user_id" not in st.session_state and selected_user is not None:
    st.session_state.current_user_id = selected_user["id"]

if selected_user is not None and st.session_state.get("current_user_id") != selected_user["id"]:
    st.session_state.current_user_id = selected_user["id"]

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
    if "reminder_time_digits" not in st.session_state:
        st.session_state.reminder_time_digits = datetime.now().strftime("%H%M")

    name = st.text_input("Habit name")
    quick_time = st.selectbox("Quick time", QUICK_TIME_OPTIONS, key="quick_time")

    preset_hhmm = get_preset_hhmm(quick_time)
    if preset_hhmm is not None:
        st.session_state.reminder_time_digits = hhmm_to_digits(preset_hhmm)

    reminder_time_digits_input = st.text_input(
        "Reminder time (4 digits HHMM)",
        key="reminder_time_digits",
        placeholder="2137",
    )

    reminder_time_digits = "".join(ch for ch in reminder_time_digits_input if ch.isdigit())[:4]
    if reminder_time_digits != reminder_time_digits_input:
        st.session_state.reminder_time_digits = reminder_time_digits

    if len(reminder_time_digits) == 4:
        st.caption(f"Formatted time: {digits_to_hhmm(reminder_time_digits)}")

    submitted = st.form_submit_button("Add")

if submitted:
    cleaned_name = name.strip()
    hhmm_digits = st.session_state.get("reminder_time_digits", "")
    if current_user_id is None:
        st.error("Please save/select a user in the sidebar first.")
    elif not cleaned_name:
        st.error("Habit name cannot be empty.")
    elif len(hhmm_digits) != 4:
        st.error("Reminder time must contain exactly 4 digits, for example 2137.")
    else:
        hhmm = digits_to_hhmm(hhmm_digits)
        if not is_valid_hhmm(hhmm):
            st.error("Reminder time must be valid (hours 00-23 and minutes 00-59).")
        else:
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