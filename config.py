import os

# Telegram API और Bot Settings
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# बोट यूजरनेम
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# Database Settings
DATABASE_URI = os.environ.get("DATABASE_URI", "")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "bot_db")

# Channel & Admin Settings
admin_ids_raw = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0  # सिंगल एडमिन सपोर्ट के लिए

# चैनल्स के लिए सुरक्षित कन्वर्जन
DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", 0))

# --- LOG_CHANNEL स्मार्ट अपडेट ---
log_channel_raw = os.environ.get("LOG_CHANNEL", "0")
if not log_channel_raw or log_channel_raw == "0":
    LOG_CHANNEL = 0
elif log_channel_raw.lstrip('-').isdigit():
    LOG_CHANNEL = int(log_channel_raw)
elif "t.me/" in log_channel_raw:
    LOG_CHANNEL = "@" + log_channel_raw.strip("/").split("t.me/")[-1]
elif not log_channel_raw.startswith("@"):
    LOG_CHANNEL = "@" + log_channel_raw
else:
    LOG_CHANNEL = log_channel_raw

# FORCE_SUB_CHANNEL सेटिंग
FORCE_SUB_CHANNEL_RAW = os.environ.get("FORCE_SUB_CHANNEL", "0")
if FORCE_SUB_CHANNEL_RAW == "0" or not FORCE_SUB_CHANNEL_RAW:
    FORCE_SUB_CHANNEL = None
elif FORCE_SUB_CHANNEL_RAW.lstrip('-').isdigit():
    FORCE_SUB_CHANNEL = int(FORCE_SUB_CHANNEL_RAW)
else:
    FORCE_SUB_CHANNEL = FORCE_SUB_CHANNEL_RAW 

FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/YourChannelUsername")
FORCE_SUB_ENABLED = os.environ.get("FORCE_SUB_ENABLED", "True").lower() == "true"
START_MESSAGE = os.environ.get("START_MESSAGE", "नमस्ते! मैं फाइल सर्च बॉट हूँ।")
SEARCH_LIMIT = int(os.environ.get("SEARCH_LIMIT", 10))

# Shortener Settings (Render variables)
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")

# Verification Time in Hours (Render Variable)
VERIFY_EXPIRE_HOURS = os.environ.get("VERIFY_EXPIRE_HOURS", "24")

# Server Port & SSL Settings
PORT = int(os.environ.get("PORT", 10000))
HAS_SSL = os.environ.get("HAS_SSL", "False").lower() == "true"

# Auto Delete Time & Tutorial Link
AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", 3600))
TUTORIAL_URL = os.environ.get("TUTORIAL_URL", "")

# --- Missing Keys Detection (कौन सी कीज़ गायब हैं उनकी लिस्ट) ---
missing_keys = []
config_dict = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "DATABASE_URI": DATABASE_URI,
    "SHORTENER_API": SHORTENER_API,
    "SHORTENER_WEBSITE": SHORTENER_WEBSITE,
}

for key, value in config_dict.items():
    if not value:
        missing_keys.append(key)

# सुरक्षित टाइप कन्वर्जन
API_ID = int(API_ID) if API_ID and str(API_ID).isdigit() else 0
VERIFY_EXPIRE_HOURS = int(VERIFY_EXPIRE_HOURS) if VERIFY_EXPIRE_HOURS and str(VERIFY_EXPIRE_HOURS).isdigit() else 24
VERIFY_EXPIRE_TIME = VERIFY_EXPIRE_HOURS * 3600  # सेकंड्स में कन्वर्ट
