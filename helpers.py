import aiohttp
import logging
import re
from typing import Optional, Dict, Any
from pyrogram.types import Message
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेटअप
logger = logging.getLogger(__name__)

# नाम को साफ़ करने के लिए (सर्चिंग आसान बनाने के लिए)
def clean_file_name(name: str) -> str:
    # फाइल नाम से फालतू स्पेशल कैरेक्टर्स और इमोजी हटाना
    name = re.sub(r"[@#$\n\r]", " ", name) 
    # फाइल के एक्स्टेंशन से पहले के फालतू डॉट्स हटाना
    name = re.sub(r"\.\.+", ".", name)
    # डबल स्पेस को सिंगल स्पेस में बदलना
    name = re.sub(r"\s+", " ", name)
    return name.strip()

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    # यदि API की नहीं है, तो ओरिजिनल URL ही वापस कर दें
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    try:
        async with aiohttp.ClientSession() as session:
            # API URL का स्ट्रक्चर प्रीमियम ऑटोटिलटर के हिसाब से
            api_url = f"{SHORTENER_WEBSITE.rstrip('/')}/api"
            params = {"api": SHORTENER_API, "url": url}
            
            async with session.get(api_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # रिस्पॉन्स के अलग-अलग फॉर्मेट को हैंडल करना
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
    # फाइल ऑब्जेक्ट को सुरक्षित रूप से चेक करना
    media = message.document or message.video or message.audio or message.photo
    if not media:
        return None
    
    # फाइल का टाइप डिसाइड करना
    file_type = "document"
    if message.video: file_type = "video"
    elif message.audio: file_type = "audio"
    elif message.photo: file_type = "photo"

    # फाइल का नाम निकालना
    file_name = getattr(media, "file_name", None)
    if not file_name:
        file_name = message.caption if message.caption else f"{file_type.capitalize()}_File"
        
    # नाम को क्लीन करना (ताकि सर्चिंग में दिक्कत न हो)
    clean_name = clean_file_name(file_name)
    
    # थंबनेल आईडी निकालना
    thumb_id = None
    if hasattr(media, "thumbs") and media.thumbs:
        thumb_id = media.thumbs[0].file_id
    elif message.photo:
        thumb_id = message.photo[-1].file_id
        
    return {
        "file_id": media.file_id,
        "name": clean_name,
        "file_type": file_type,
        "file_size": getattr(media, "file_size", 0),
        "thumb_id": thumb_id,
        "message_id": message.id
    }
    
