import aiohttp
from config import SHORTENER_API, SHORTENER_WEBSITE

# 1. शॉर्टनर लिंक जेनरेट करने के लिए फंक्शन
async def get_shortlink(url):
    # अगर API या URL सेट नहीं है, तो शॉर्टनर का उपयोग न करें
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url
    
    api_url = f"{SHORTENER_WEBSITE}/api?api={SHORTENER_API}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                # ज्यादातर शॉर्टनर API में 'shortenedUrl' या 'shorturl' की होती है
                return data.get("shortenedUrl", url)
    except Exception as e:
        print(f"Shortener Error: {e}")
        return url

# 2. फाइल का नाम या जानकारी निकालने के लिए (Optional पर उपयोगी)
async def get_file_info(message):
    file = message.document or message.video or message.audio
    return {
        "file_id": file.file_id,
        "file_name": getattr(file, "file_name", "Unknown_File"),
        "file_size": getattr(file, "file_size", 0)
    }
    
