import aiohttp
import logging
import re
from typing import Optional, Dict, Any
from pyrogram.types import Message
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेटअप
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# नाम को साफ़ करने के लिए (सर्चिंग आसान बनाने के लिए)
def clean_file_name(name: str) -> str:
    name = re.sub(r"[@#$]", "", name) # @, #, $ जैसे निशान हटाता है
    return name.strip()

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    try:
        async with aiohttp.ClientSession() as session:
            api_url = f"{SHORTENER_WEBSITE.rstrip('/')}/api"
            params = {"api": SHORTENER_API, "url": url}
            
            async with session.get(api_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    shortened = data.get("shortenedUrl") or data.get("shorturl") or data.get("link")
                    return shortened if shortened else url
                else:
                    logger.warning(f"⚠️ शॉर्टनर रिस्पॉन्स स्टेटस: {response.status}")
                    return url
    except Exception as e:
        logger.error(f"❌ शॉर्टनर API में एरर: {e}")
        return url

# 2. फाइल की जानकारी (Updated)
async def get_file_info(message: Message) -> Optional[Dict[str, Any]]:
    file_type = None
    if message.document:
        file = message.document
        file_type = "document"
    elif message.video:
        file = message.video
        file_type = "video"
    elif message.audio:
        file = message.audio
        file_type = "audio"
    elif message.photo:
        file = message.photo[-1]
        file_type = "photo"
    else:
        return None
    
    default_name = f"{file_type.capitalize()}_Message"
    if hasattr(file, "file_name"):
        default_name = file.file_name
        
    # नाम को क्लीन करके सेव करें
    file_name = clean_file_name(message.caption or default_name)
    
    thumb_id = None
    if hasattr(file, "thumbs") and file.thumbs:
        thumb_id = file.thumbs[0].file_id
    elif message.photo:
        thumb_id = message.photo[-1].file_id
        
    return {
        "file_id": file.file_id,
        "name": file_name,
        "file_type": file_type,
        "file_size": getattr(file, "file_size", 0),
        "thumb_id": thumb_id,
        "message_id": message.id
    }
    
