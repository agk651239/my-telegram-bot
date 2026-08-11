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
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0

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

# --- Force Channels (Public और Private दोनों सपोर्ट के साथ) ---
public_raw = os.environ.get("PUBLIC_FORCE_CHANNELS", "").strip()
if public_raw.lower() in ["false", "none", "off", ""]:
    PUBLIC_CHANNELS = []
else:
    PUBLIC_CHANNELS = [ch.strip() for ch in public_raw.split(",") if ch.strip()]

private_raw = os.environ.get("PRIVATE_FORCE_CHANNELS", "").strip()
if private_raw.lower() in ["false", "none", "off", ""]:
    PRIVATE_CHANNELS = []
else:
    # यदि आईडी संख्या में है (जैसे -100... तो उसे इंटीजर में बदलें, नहीं तो स्ट्रिंग रहने दें)
    PRIVATE_CHANNELS = [int(ch.strip()) if ch.strip().lstrip('-').isdigit() else ch.strip() for ch in private_raw.split(",") if ch.strip()]

FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/YourChannelUsername")
FORCE_SUB_ENABLED = os.environ.get("FORCE_SUB_ENABLED", "True").lower() == "true"
START_MESSAGE = os.environ.get("START_MESSAGE", "नमस्ते! मैं फाइल सर्च बॉट हूँ।")
SEARCH_LIMIT = int(os.environ.get("SEARCH_LIMIT", 10))

# Shortener Settings (Render variables)
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")
SHORTENER_URL = os.environ.get("SHORTENER_URL", "")

# Verification Time in Hours (Render Variable) & Tutorial Link
VERIFY_EXPIRE_HOURS = os.environ.get("VERIFY_EXPIRE_HOURS", "24")
HOW_TO_VERIFY_LINK = os.environ.get("HOW_TO_VERIFY_LINK", "")
TUTORIAL_URL = os.environ.get("TUTORIAL_URL", "")

# Server Port & SSL Settings
PORT = int(os.environ.get("PORT", 10000))
HAS_SSL = os.environ.get("HAS_SSL", "False").lower() == "true"
AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", 3600))

# --- Missing Keys Detection ---
missing_keys = []
config_dict = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "DATABASE_URI": DATABASE_URI,
    "ADMIN_IDS": admin_ids_raw,
    "LOG_CHANNEL": log_channel_raw,
    "DATABASE_CHANNEL": DATABASE_CHANNEL,
    "VERIFY_EXPIRE_HOURS": VERIFY_EXPIRE_HOURS,
    "SHORTENER_API": SHORTENER_API,
    "SHORTENER_WEBSITE": SHORTENER_WEBSITE,
    "TUTORIAL_URL": TUTORIAL_URL,
}

for key, value in config_dict.items():
    if not value or str(value).strip() in ["0", "", "None"]:
        missing_keys.append(key)

# सुरक्षित टाइप कन्वर्जन
API_ID = int(API_ID) if API_ID and str(API_ID).isdigit() else 0
VERIFY_EXPIRE_HOURS = int(VERIFY_EXPIRE_HOURS) if VERIFY_EXPIRE_HOURS and str(VERIFY_EXPIRE_HOURS).isdigit() else 24
VERIFY_EXPIRE_TIME = VERIFY_EXPIRE_HOURS * 3600  # सेकंड्स में कन्वर्ट


# =========================================================================
# 🆕 नए फीचर्स के लिए एक्स्ट्रा सेटिंग्स (यहाँ से नीचे नए पॉइंट्स जोड़े गए हैं)
# =========================================================================

# पेमेंट और यूपीआई आईडी (आप चाहें तो एनवायरनमेंट वेरिएबल से लें या यहाँ डायरेक्ट लिख सकते हैं)
UPI_ID = os.environ.get("UPI_ID", "agk651239@nyes") # अपनी UPI ID यहाँ डालें
PAYMENT_QR_DEFAULT = os.environ.get("PAYMENT_QR_DEFAULT", "") # डिफ़ॉल्ट QR फोटो फाइल आईडी (अगर हो)
