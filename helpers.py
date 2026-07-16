import aiohttp
import logging
from typing import Optional, Dict, Any
from pyrogram.types import Message
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेट करें ताकि एरर और वार्निंग का रिकॉर्ड रहे
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    """
    यूजर को वेरिफिकेशन के लिए शॉर्ट लिंक जनरेट करके देता है।
    """
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    api_url = f"{SHORTENER_WEBSITE}/api"
    params = {"api": SHORTENER_API, "url": url}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    shortened = data.get("shortenedUrl") or data.get("shorturl") or data.get("link")
                    return shortened if shortened else url
                else:
                    logger.warning(f"Shortener returned status {response.status}")
                    return url
    except Exception as e:
        logger.error(f"Shortener API Error: {e}")
        return url

# 2. फाइल की जानकारी (इंडेक्सिंग के लिए)
async def get_file_info(message: Message) -> Optional[Dict[str, Any]]:
    """
    Telegram मैसेज से फाइल डिटेल्स सुरक्षित तरीके से निकालता है।
    """
    # सपोर्टेड फाइल टाइप्स
    file = message.document or message.video or message.audio or message.photo
    
    if not file:
        return None
    
    # फाइल का नाम: कैप्शन, फिर फाइल का नाम, फिर 'Unnamed'
    # .strip() का उपयोग फालतू स्पेस हटाने के लिए किया गया है
    file_name = (message.caption or getattr(file, "file_name", "Unnamed_File")).strip()
    
    # थंबनेल का ID सुरक्षित तरीके से निकालना
    thumb_id = None
    if hasattr(file, "thumbs") and file.thumbs:
        thumb_id = file.thumbs[0].file_id
    elif message.photo:
        thumb_id = message.photo[-1].file_id
        
    return {
        "file_id": file.file_id,
        "name": file_name,
        "file_size": getattr(file, "file_size", 0),
        "thumb_id": thumb_id
    }

