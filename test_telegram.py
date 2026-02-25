from telegram_bot import send_message


CHAT_ID = "996868615"

response = send_message(CHAT_ID, "Test message from Habit Tracker MVP")
print(response)