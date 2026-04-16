import os


# =====================================================
# TELEGRAM
# =====================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")


# =====================================================
# WEBHOOK
# =====================================================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


# =====================================================
# GOOGLE SHEETS
# =====================================================
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# ⚠️ ЭТО ИМЕННО ID таблицы (НЕ ссылка!)
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")


# =====================================================
# VALIDATION (чтобы больше не страдать)
# =====================================================
def validate_config():
    errors = []

    if not BOT_TOKEN:
        errors.append("BOT_TOKEN missing")

    if not WEBHOOK_URL:
        errors.append("WEBHOOK_URL missing")

    if not GOOGLE_CREDENTIALS:
        errors.append("GOOGLE_CREDENTIALS missing")

    if not SPREADSHEET_NAME:
        errors.append("SPREADSHEET_NAME missing")

    if errors:
        raise ValueError("❌ CONFIG ERROR:\n" + "\n".join(errors))


validate_config()
