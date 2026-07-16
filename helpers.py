import aiohttp
import logging
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेट करें ताकि एरर और वार्निंग का रिकॉर्ड रहे
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url: str) -> str:
    """
    यूजर को वेरिफिकेशन के लिए शॉर्ट लिंक जनरेट करके देता है।
    """
    # अगर API या URL सेट नहीं है, तो बिना शॉर्ट किए ओरिजिनल लिंक ही भेजें
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    # API URL का निर्माण (Query parameters)
    api_url = f"{SHORTENER_WEBSITE}/api"
    params = {"api": SHORTENER_API, "url": url}
    
    try:
        async with aiohttp.ClientSession() as session:
            # 10 सेकंड का टाइमआउट लगाया ताकि बोट हैंग न हो
            async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    # शॉर्टनर रिस्पॉन्स में अलग-अलग कीज़ (keys) को चेक करना
                    shortened = data.get("shortenedUrl") or data.get("shorturl") or data.get("link")
                    return shortened if shortened else url
                else:
                    logger.warning(f"Shortener returned status {response.status}")
                    return url
    except Exception as e:
        logger.error(f"Shortener API Error: {e}")
        return url

# 2. फाइल की जानकारी (इंडेक्सिंग के लिए)
async def get_file_info(message):
    """
    Telegram मैसेज से फाइल डिटेल्स निकालता है।
    """
    # फाइल को पहचानें
    file = message.document or message.video or message.audio or message.photo
    
    # अगर फाइल नहीं मिलती, तो None भेजें
    if not file:
        return None
    
    # फाइल का नाम निकालना (कैप्शन को प्राथमिकता दें)
    file_name = message.caption if message.caption else getattr(file, "file_name", "Unnamed_File")
    
    # थंबनेल का ID निकालना
    thumb_id = None
    if hasattr(file, "thumbs") and file.thumbs:
        # वीडियो/डॉक्यूमेंट का थंबनेल
        thumb_id = file.thumbs[0].file_id
    elif message.photo:
        # अगर फोटो ही फाइल है, तो उसकी आखिरी सबसे बड़ी ID
        thumb_id = message.photo[-1].file_id
        
    return {
        "file_id": file.file_id,
        "name": file_name,
        "file_size": getattr(file, "file_size", 0),
        "thumb_id": thumb_id
    }
    
