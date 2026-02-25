import os
from datetime import datetime

from dotenv import load_dotenv

from database import get_chat_id_for_habit, get_habits, log_reminder_sent, was_reminder_sent
from telegram_bot import send_message


load_dotenv()


def normalize_hhmm(value: str) -> str:
  raw_value = value.strip()
  parts = raw_value.split(":")

  if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
    raise ValueError(f"Invalid time format: {value}. Expected HH:MM.")

  hours = int(parts[0])
  minutes = int(parts[1])

  if not (0 <= hours <= 23 and 0 <= minutes <= 59):
    raise ValueError(f"Invalid time value: {value}. Expected 00:00-23:59.")

  return f"{hours:02d}:{minutes:02d}"


def run_reminder_check(now_hhmm: str | None = None) -> int:
  now_dt = datetime.now()
  current_hhmm = normalize_hhmm(now_hhmm) if now_hhmm is not None else now_dt.strftime("%H:%M")
  sent_at = f"{now_dt.strftime('%Y-%m-%d')} {current_hhmm}"
  habits = get_habits()

  sent_count = 0
  for habit in habits:
    if "is_active" in habit.keys() and not bool(habit["is_active"]):
      continue

    habit_hhmm = normalize_hhmm(habit["reminder_time"])
    if habit_hhmm != current_hhmm:
      continue

    if was_reminder_sent(habit["id"], sent_at):
      continue

    chat_id = get_chat_id_for_habit(habit["id"])
    if not chat_id:
      fallback_chat_id = os.getenv("TELEGRAM_CHAT_ID")
      if fallback_chat_id:
        chat_id = fallback_chat_id
      else:
        continue

    message = f"Reminder: {habit['name']} (time {current_hhmm})"
    try:
      send_message(chat_id, message)
      log_reminder_sent(habit["id"], sent_at)
    except Exception as exc:
      raise RuntimeError(
        f"Failed to send reminder for habit '{habit['name']}' at {current_hhmm}: {exc}"
      ) from exc

    sent_count += 1

  return sent_count
