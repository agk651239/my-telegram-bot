import os

# Telegram API और Bot Settings
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# बोट यूजरनेम
BOT_USERNAME = os.environ.get("BOT_USERNAME", "YourBotUsername")

# Database Settings
DATABASE_URI = os.environ.get("DATABASE_URI", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "bot_db")

# Channel & Admin Settings
admin_ids_raw = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

# चैनल्स के लिए सुरक्षित कन्वर्जन
DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", 0))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))

# FORCE_SUB_CHANNEL सेटिंग
FORCE_SUB_CHANNEL_RAW = os.environ.get("FORCE_SUB_CHANNEL", "0")
if FORCE_SUB_CHANNEL_RAW.isdigit():
    FORCE_SUB_CHANNEL = int(FORCE_SUB_CHANNEL_RAW)
else:
    FORCE_SUB_CHANNEL = FORCE_SUB_CHANNEL_RAW 

# --- नई सेटिंग्स जोड़ी गई हैं ---
# 1. Force Sub को ON/OFF करने के लिए
FORCE_SUB_ENABLED = os.environ.get("FORCE_SUB_ENABLED", "True").lower() == "true"

# 2. वेलकम मैसेज मोड (बोट स्टार्ट होने पर मैसेज दिखाए या नहीं)
START_MESSAGE = os.environ.get("START_MESSAGE", "नमस्ते! मैं फाइल सर्च बॉट हूँ।")

# 3. सर्च रिजल्ट लिमिट (एक बार में कितनी फाइलें दिखें)
SEARCH_LIMIT = int(os.environ.get("SEARCH_LIMIT", 10))

# Shortener Settings
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")

# Server Port & SSL Settings
PORT = int(os.environ.get("PORT", 10000))
HAS_SSL = os.environ.get("HAS_SSL", "False").lower() == "true"

# Time Settings (सेकंड्स में)
VERIFY_EXPIRE_TIME = int(os.environ.get("VERIFY_EXPIRE_TIME", 86400)) # 24 घंटे
AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", 3600))     # 1 घंटा
