import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPERATOR_ID = int(os.getenv("OPERATOR_ID", "0"))
