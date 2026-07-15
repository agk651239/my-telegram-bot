import os

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DATABASE_URI = os.environ.get("DATABASE_URI", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "bot_db")
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",")]
DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", 0))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "") # चैनल का यूजरनेम डालें (जैसे: @YourChannel)
