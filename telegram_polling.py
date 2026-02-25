import os
import time

import requests
from dotenv import load_dotenv

from database import init_db, upsert_user
from telegram_bot import send_message


def run_polling() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing. Add it to your .env file.")

    init_db()
    base_url = f"https://api.telegram.org/bot{token}"
    last_update_id = None

    print("[polling] started")
    while True:
        try:
            params = {"timeout": 0}
            if last_update_id is not None:
                params["offset"] = last_update_id + 1

            response = requests.get(f"{base_url}/getUpdates", params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()

            if not payload.get("ok", False):
                print(f"[polling] Telegram API error: {payload}")
                time.sleep(5)
                continue

            updates = payload.get("result", [])
            for update in updates:
                update_id = update.get("update_id")
                if update_id is not None:
                    last_update_id = update_id

                message = update.get("message", {})
                text = (message.get("text") or "").strip()
                if text != "/start":
                    continue

                chat = message.get("chat", {})
                chat_id = chat.get("id")
                first_name = message.get("from", {}).get("first_name") or "User"

                if chat_id is None:
                    print("[polling] /start received but chat_id is missing")
                    continue

                user_id = upsert_user(name=first_name, chat_id=str(chat_id))
                send_message(chat_id, f"Hi, {first_name}! You are registered. (user_id={user_id})")
                print(f"[polling] registered user_id={user_id}, chat_id={chat_id}, name={first_name}")

        except Exception as exc:
            print(f"[polling] error: {exc}")

        time.sleep(5)


if __name__ == "__main__":
    run_polling()