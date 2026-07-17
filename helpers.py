import aiohttp
import logging
from typing import Optional, Dict, Any
from pyrogram.types import Message
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेटअप
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    """
    यूजर को वेरिफिकेशन के लिए शॉर्ट लिंक जनरेट करके देता है।
    """
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SHORTENER_WEBSITE}/api", 
                params={"api": SHORTENER_API, "url": url}, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    shortened = data.get("shortenedUrl") or data.get("shorturl") or data.get("link")
                    return shortened if shortened else url
                else:
                    logger.warning(f"⚠️ शॉर्टनर का रेस्पोंस स्टेटस: {response.status}")
                    return url
                    
    except Exception as e:
        logger.error(f"❌ शॉर्टनर API में एरर: {e}")
        return url

# 2. फाइल की जानकारी (इंडेक्सिंग के लिए)
async def get_file_info(message: Message) -> Optional[Dict[str, Any]]:
    """
    Telegram मैसेज से फाइल डिटेल्स और message_id निकालता है।
    """
    # सपोर्टेड फाइल टाइप्स
    file = message.document or message.video or message.audio
    
    if not file:
        return None
    
    # फाइल का नाम
    file_name = (message.caption or getattr(file, "file_name", "Unnamed_File")).strip()
    
    # थंबनेल का ID
    thumb_id = None
    if hasattr(file, "thumbs") and file.thumbs:
        thumb_id = file.thumbs[0].file_id
    elif message.photo:
        thumb_id = message.photo[-1].file_id
        
    return {
        "file_id": file.file_id,
        "name": file_name,
        "file_size": getattr(file, "file_size", 0),
        "thumb_id": thumb_id,
        "message_id": message.id  # Yeh line copy_message ke liye zaroori hai
    }
    
