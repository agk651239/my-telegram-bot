import requests
import os
import time

# 1. Shortlink Generate करने का फंक्शन
def get_shortlink(user_id):
    api_key = os.environ.get("SHORTENER_API")
    api_url = os.environ.get("SHORTENER_WEBSITE")
    # यूजर को एक यूनिक लिंक देंगे जिसे क्लिक करने पर वह वेरीफाई होगा
    url = f"https://t.me/YOUR_BOT_USERNAME?start=verify_{user_id}"
    
    try:
        # शॉर्टनर वेबसाइट को रिक्वेस्ट भेजें
        resp = requests.get(f"{api_url}/api?api={api_key}&url={url}").json()
        if resp.get("status") == "success":
            return resp.get("shortenedUrl")
    except:
        pass
    return url # अगर API काम न करे, तो ओरिजिनल लिंक दे

# 2. वीडियो का विवरण (Name, Size, Thumbnail) निकालने का फंक्शन
def get_file_info(message):
    media = message.video or message.document
    file_name = media.file_name if hasattr(media, 'file_name') else "Video File"
    file_size = f"{round(media.file_size / (1024 * 1024), 2)} MB"
    return file_name, file_size
  
