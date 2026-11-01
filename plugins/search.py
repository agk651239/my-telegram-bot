from pyrogram import filters, types
import asyncio
import logging
from humanfriendly import format_size
from natsort import natsorted  # <-- यह नई लाइब्रेरी जोड़ी गई है
from config import BOT_USERNAME, DATABASE_CHANNEL, LOG_CHANNEL, ADMIN_IDS
from database import db
from helpers import get_file_info, add_file, clean_file_name

# एल्बम प्रोसेसिंग के लिए सेट
processed_albums = set()

# --- फाइल इंडेक्सिंग (यह आपके main.py से यहाँ आया है) ---
async def index_files(client, message):
    if message.media_group_id:
        if message.media_group_id in processed_albums:
            return
        processed_albums.add(message.media_group_id)
        await asyncio.sleep(2)
        try:
            media_group = await client.get_media_group(message.chat.id, message.id)
            caption = None
            for m in media_group:
                if m.caption:
                    caption = m.caption
                    break
            for m in media_group:
                if caption:
                    m.caption = caption
                file_info = await get_file_info(m)
                if file_info:
                    file_info["media_group_id"] = message.media_group_id
                    await add_file(file_info)
            
            try:
                await client.send_message(LOG_CHANNEL, f"🎞️ **Album Upload Successfully** (Group ID: `{message.media_group_id}`)")
            except Exception as e:
                logging.error(f"Log Error (Album Upload): {e}")

        except Exception as e:
            logging.error(f"Album Indexing Error: {e}")

# --- ऑटो सर्च (यहाँ सॉर्टिंग फिक्स हुई है) ---
async def auto_search(client, message):
    user_id = message.from_user.id
    
    # 1. यदि एडमिन लाइव चैट मोड में है तो मैसेज सीधे यूजर को जाए
    if user_id in ADMIN_IDS:
        live_data = await db.settings.find_one({"type": "live_chat"})
        if live_data and live_data.get("active_admin") == user_id:
            u_id = live_data.get("active_user")
            if u_id:
                try:
                    await message.copy(u_id)
                    return
                except Exception as e:
                    await message.reply(f"❌ यूजर को भेजने में एरर: {e}")
                    return

    # 2. यदि यूजर लाइव चैट मोड में है तो मैसेज सीधे एडमिन को जाए
    live_data = await db.settings.find_one({"type": "live_chat"})
    if live_data and live_data.get("active_user") == user_id:
        adm = live_data.get("active_admin")
        if adm:
            try:
                await message.forward(adm)
                return
            except:
                pass

    if user_id not in ADMIN_IDS:
        return

    query = message.text
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=30000)
    if not files: 
        return await message.reply("❌ कोई फाइल नहीं मिली। / No file found.")
    
    # ==========================================
    # 🆕 यहाँ natsorted का जादू है (1, 2, 10, 11 के लिए)
    files = natsorted(files, key=lambda x: x.get("name", ""))
    # ==========================================

    buttons = []
    processed_groups = set()
    
    for f in files:
        if f.get("media_group_id"):
            if f["media_group_id"] not in processed_groups:
                album_link = f"https://t.me/{BOT_USERNAME}?start=getalbum_{f['media_group_id']}"
                btn = [types.InlineKeyboardButton(f"📥 Album: {f['name']}", url=album_link)]
                buttons.append(btn)
                processed_groups.add(f["media_group_id"])
        else:
            unique_link = f"https://t.me/{BOT_USERNAME}?start=getfile_{f['_id']}"
            file_size = format_size(f.get("file_size", 0))
            btn = [types.InlineKeyboardButton(f"📥 File: {f['name']} ({file_size})", url=unique_link)]
            buttons.append(btn)

    await message.reply(f"📂 **'{query}' के लिए रिजल्ट्स:**", reply_markup=types.InlineKeyboardMarkup(buttons))

# --- हैंडलर्स को रजिस्टर करना ---
def register_search_handlers(app):
    # इंडेक्सिंग हैंडलर
    app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video | filters.photo))(index_files)
    
    # सर्च हैंडलर (इसमें सभी कमांड्स को छोड़ दिया गया है ताकि वे अलग से काम करें)
    app.on_message(filters.text & ~filters.command([
        "start", "broadcast", "stats", "help", "setprice", "updateprice", 
        "nobypass", "set_qr", "connect", "problemsolve", "myplan", 
        "pricing", "plans", "users", "addadmin", "removeadmin"
    ]))(auto_search)
