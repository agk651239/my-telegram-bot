import aiohttp, logging
from typing import Optional, Dict, Any
from pyrogram.types import Message
from config import SHORTENER_API, SHORTENER_WEBSITE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    if not SHORTENER_API or not SHORTENER_WEBSITE: return url
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHORTENER_WEBSITE}/api", params={"api": SHORTENER_API, "url": url}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("shortenedUrl") or data.get("shorturl") or data.get("link") or url
                logger.warning(f"Shortener Status: {resp.status}")
    except Exception as e: logger.error(f"Shortener API Error: {e}")
    return url

# 2. फाइल की जानकारी (इंडेक्सिंग के लिए)
async def get_file_info(message: Message) -> Optional[Dict[str, Any]]:
    file = message.document or message.video or message.audio or message.photo
    if not file: return None
    
    thumb_id = None
    if hasattr(file, "thumbs") and file.thumbs: thumb_id = file.thumbs[0].file_id
    elif message.photo: thumb_id = message.photo[-1].file_id
        
    return {
        "file_id": file.file_id,
        "name": (message.caption or getattr(file, "file_name", "Unnamed_File")).strip(),
        "file_size": getattr(file, "file_size", 0),
        "thumb_id": thumb_id
    }


