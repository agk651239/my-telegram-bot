import aiohttp
from config import SHORTENER_API, SHORTENER_WEBSITE

# शॉर्टनर लिंक जेनरेट करने के लिए
async def get_shortlink(url):
    if not SHORTENER_API or not SHORTENER_WEBSITE:
        return url # अगर API नहीं है, तो ओरिजिनल लिंक ही भेजें
    
    api_url = f"{SHORTENER_WEBSITE}/api?api={SHORTENER_API}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                return data.get("shortenedUrl", url)
    except:
        return url

# फाइल की जानकारी के लिए (अगर आपको जरूरत हो)
async def get_file_info(message):
    file = message.document or message.video or message.audio
    return {
        "file_id": file.file_id,
        "file_name": getattr(file, "file_name", "Unknown_File"),
        "file_size": getattr(file, "file_size", 0)
    }
    
