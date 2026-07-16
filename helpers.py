import aiohttp
import logging
from config import SHORTENER_API, SHORTENER_WEBSITE

# लॉगिंग सेट करें ताकि एरर का पता चल सके
logger = logging.getLogger(__name__)

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url):
    # अगर API या URL सेट नहीं है, तो सीधे लिंक रिटर्न करें
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    # API URL का निर्माण (ज्यादातर शॉर्टनर्स इसी फॉर्मेट पर काम करते हैं)
    api_url = f"{SHORTENER_WEBSITE}/api?api={SHORTENER_API}&url={url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # 10 सेकंड का टाइमआउट लगाया ताकि बोट हैंग न हो
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    # शॉर्टनर रिस्पॉन्स में अलग-अलग कीज़ हो सकती हैं, सबसे कॉमन चेक करें
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
    # सपोर्टेड फाइल टाइप्स
    file = message.document or message.video or message.audio or message.photo
    
    # अगर फाइल का नाम नहीं मिल रहा तो 'Unnamed File' सेट करें
    file_name = None
    if message.caption:
        file_name = message.caption
    elif hasattr(file, "file_name"):
        file_name = file.file_name
    else:
        file_name = "Unnamed_File"
        
    return {
        "file_id": file.file_id,
        "name": file_name,
        "file_size": getattr(file, "file_size", 0)
    }
    
