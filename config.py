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
# सुरक्षित तरीके से ADMIN_IDS को लिस्ट में बदलना
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

# चैनल्स के लिए सुरक्षित कन्वर्जन (अगर आईडी खाली है तो None रखें)
DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", 0))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))

# FORCE_SUB_CHANNEL (अगर आईडी सेट नहीं है तो 0 रखें)
FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", 0))

# Shortener Settings
SHORTENER_API = os.environ.get("SHORTENER_API", "")
SHORTENER_WEBSITE = os.environ.get("SHORTENER_WEBSITE", "")

# Server Port (Render के लिए जरूरी)
PORT = int(os.environ.get("PORT", 8080))

# Time Settings (सेकंड्स में)
VERIFY_EXPIRE_TIME = int(os.environ.get("VERIFY_EXPIRE_TIME", 86400)) # 24 घंटे
AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", 3600))     # 1 घंटा
