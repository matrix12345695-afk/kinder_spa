import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPERATOR_ID = int(os.getenv("OPERATOR_ID", "0"))

# 👇 ВОТ ЭТО ДОБАВЬ
GOOGLE_SHEET_NAME = os.getenv("SPREADSHEET_NAME", "kinder_spa")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "credentials.json")
