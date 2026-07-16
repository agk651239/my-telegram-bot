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
# ADMIN_IDS को सुरक्षित रूप से हैंडल करने के लिए चेक लगाया गया है
admin_ids_raw = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in admin_ids_raw.split(",")] if admin_ids_raw else []

DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", 0))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", None)

# Shortener Settings (API और Website URL)
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")

# Server Port (Render या अन्य होस्टिंग के लिए)
PORT = int(os.environ.get("PORT", 10000))

# Time Settings (सेकंड्स में)
# VERIFY_EXPIRE_TIME: यूजर वेरिफिकेशन कितनी देर तक चलेगा (86400 = 24 घंटे)
VERIFY_EXPIRE_TIME = int(os.environ.get("VERIFY_EXPIRE_TIME", 86400))

# FILE_DELETE_TIME: फाइल भेजने के बाद कितनी देर में डिलीट होगी (3600 = 1 घंटा)
FILE_DELETE_TIME = int(os.environ.get("FILE_DELETE_TIME", 3600))
