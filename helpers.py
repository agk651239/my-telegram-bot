import aiohttp
import logging
import re
from typing import Optional, Dict, Any
from pyrogram.types import Message
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेटअप
logger = logging.getLogger(__name__)

# नाम को साफ़ करने के लिए फंक्शन
def clean_file_name(name: str) -> str:
    if not name: return "Untitled" # खाली नाम होने पर डिफॉल्ट नाम
    # फाइल नाम से फालतू स्पेशल कैरेक्टर्स और इमोजी हटाना
    name = re.sub(r"[@#$|_\n\r]", " ", name) 
    # कोष्ठक और ब्रैकेट के अंदर का कंटेंट हटाना
    name = re.sub(r"\[.*?\]|\(.*?\)", "", name)
    # फाइल के एक्स्टेंशन से पहले के फालतू डॉट्स हटाना
    name = re.sub(r"\.\.+", ".", name)
    # डबल स्पेस को सिंगल स्पेस में बदलना
    name = re.sub(r"\s+", " ", name)
    return name.strip()[:100] # नाम को 100 कैरेक्टर पर काट देना (डेटाबेस के लिए सेफ)

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    try:
        async with aiohttp.ClientSession() as session:
            base_url = SHORTENER_WEBSITE.rstrip('/')
            api_url = f"{base_url}/api"
            params = {"api": SHORTENER_API, "url": url}
            
            # timeout को थोड़ा बढ़ाया है ताकि स्लो नेटवर्क पर एरर न आए
            async with session.get(api_url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    # Response JSON check
                    shortened = data.get("shortenedUrl") or data.get("shorturl") or data.get("link")
                    return shortened if shortened else url
                else:
                    logger.warning(f"⚠️ शॉर्टनर रिस्पॉन्स स्टेटस: {response.status}")
                    return url
    except Exception as e:
        logger.error(f"❌ शॉर्टनर API में एरर: {e}")
        return url

# 2. फाइल की जानकारी
async def get_file_info(message: Message) -> Optional[Dict[str, Any]]:
    # मीडिया ऑब्जेक्ट की पहचान
    media = message.document or message.video or message.audio or message.photo
    if not media:
        return None
    
    # फाइल का टाइप डिसाइड करना
    if message.document: file_type = "document"
    elif message.video: file_type = "video"
    elif message.audio: file_type = "audio"
    else: file_type = "photo"

    # फाइल का नाम निकालना
    if message.caption:
        file_name = message.caption
    else:
        # यहाँ हमने getattr का बेहतर उपयोग किया है
        file_name = getattr(media, "file_name", file_type.capitalize())
        
    # नाम को क्लीन करना
    clean_name = clean_file_name(file_name)
    
    # थंबनेल आईडी निकालने का सुरक्षित तरीका (सुधारित)
    thumb_id = None
    if message.photo:
        # यहाँ हमने चेक किया है कि क्या message.photo एक लिस्ट है
        if isinstance(message.photo, list):
            thumb_id = message.photo[-1].file_id
        else:
            thumb_id = message.photo.file_id
    elif media and getattr(media, "thumbs", None):
        # document या video के थंबनेल की जाँच
        thumbs = media.thumbs
        thumb_id = thumbs[0].file_id
        
    # यहाँ हमने सभी जरूरी जानकारी को डिक्शनरी में पैक कर दिया है
    return {
        "file_id": media.file_id, 
        "name": clean_name,
        "file_type": file_type,
        "file_size": getattr(media, "file_size", 0),
        "thumb_id": thumb_id,
        "message_id": message.id,
        "media_group_id": getattr(message, "media_group_id", None) 
    }
    
