import requests
import os
from config import BOT_USERNAME

def get_shortlink(user_id):
    api_key = os.environ.get("SHORTENER_API")
    api_url = os.environ.get("SHORTENER_WEBSITE")
    url = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
    
    try:
        resp = requests.get(f"{api_url}/api?api={api_key}&url={url}").json()
        if resp.get("status") == "success":
            return resp.get("shortenedUrl")
    except:
        pass
    return url

def get_file_info(message):
    media = message.video or message.document
    name = message.caption or "File"
    size = f"{round(media.file_size / (1024 * 1024), 2)} MB"
    return name, size
    
