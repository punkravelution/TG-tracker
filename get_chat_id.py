import os

import requests
from dotenv import load_dotenv


load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
  raise ValueError("TELEGRAM_BOT_TOKEN is missing. Add it to your .env file.")

url = f"https://api.telegram.org/bot{token}/getUpdates"
response = requests.get(url, timeout=10)
response.raise_for_status()
data = response.json()

updates = data.get("result", [])
if not updates:
  print("Send any message to the bot and run again.")
else:
  latest = updates[-1]
  chat_id = latest.get("message", {}).get("chat", {}).get("id")
  if chat_id is None:
    print("Send any message to the bot and run again.")
  else:
    print(chat_id)