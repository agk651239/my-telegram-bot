import os

# Telegram API और Bot Settings
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# Database Settings
DATABASE_URI = os.environ.get("DATABASE_URI", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "bot_db")

# Channel & Admin Settings
admin_ids_raw = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in admin_ids_raw.split(",")] if admin_ids_raw else []

DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", 0))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))

# FORCE_SUB_CHANNEL को int में बदला गया (अगर सेट है)
force_sub_raw = os.environ.get("FORCE_SUB_CHANNEL", None)
FORCE_SUB_CHANNEL = int(force_sub_raw) if force_sub_raw else None

# Shortener Settings
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")

# Server Port
PORT = int(os.environ.get("PORT", 10000))

# Time Settings (सेकंड्स में)
VERIFY_EXPIRE_TIME = int(os.environ.get("VERIFY_EXPIRE_TIME", 86400))
FILE_DELETE_TIME = int(os.environ.get("FILE_DELETE_TIME", 3600))
