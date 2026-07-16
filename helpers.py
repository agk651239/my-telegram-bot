import aiohttp
from config import SHORTENER_API, SHORTENER_WEBSITE

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url):
    # अगर API या URL सेट नहीं है, तो शॉर्टनर का उपयोग न करें
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    # कुछ शॉर्टनर वेबसाइट्स को '?' के बजाय '/' की जरूरत होती है, 
    # पर यह आपके मौजूदा सेटअप के लिए बेस्ट है
    api_url = f"{SHORTENER_WEBSITE}/api?api={SHORTENER_API}&url={url}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as response:
                data = await response.json()
                # अगर 'shortenedUrl' कीवर्ड काम न करे, तो 'shorturl' चेक करें
                return data.get("shortenedUrl") or data.get("shorturl") or url
    except Exception as e:
        print(f"Shortener API Error: {e}")
        return url

# 2. फाइल की जानकारी (इंडेक्सिंग के लिए)
async def get_file_info(message):
    file = message.document or message.video or message.audio
    return {
        "file_id": file.file_id,
        "name": getattr(message, "caption", None) or getattr(file, "file_name", "Unknown_File"),
        "file_size": getattr(file, "file_size", 0)
    }
    
