import os

import requests
from dotenv import load_dotenv


load_dotenv()


def send_message(chat_id: int | str, text: str) -> dict:
  token = os.getenv("TELEGRAM_BOT_TOKEN")
  if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing. Add it to your .env file.")

  url = f"https://api.telegram.org/bot{token}/sendMessage"
  payload = {
    "chat_id": chat_id,
    "text": text,
  }

  try:
    response = requests.post(url, data=payload, timeout=10)
    response.raise_for_status()
    result = response.json()
  except requests.RequestException as exc:
    raise RuntimeError(f"Telegram request failed: {exc}") from exc

  if not result.get("ok", False):
    description = result.get("description", "Unknown Telegram error")
    raise RuntimeError(f"Telegram API error: {description}")

  return result