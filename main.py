from pyrogram import Client, filters, types, idle
from pyrogram.errors import FloodWait
import asyncio
import logging

from config import *
from database import *
from helpers import *
from aiohttp import web

# बोट का मुख्य क्लाइंट सेटअप
app = Client(
    "bot_session", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

# लॉगिंग फंक्शन
async def send_log(client, text):
    if LOG_CHANNEL:
        try:
            await client.send_message(LOG_CHANNEL, text)
        except Exception:
            pass

# स्टार्ट कमांड
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id)
    
    if "verify_" in message.text:
        await set_verify(user_id)
        await message.reply("✅ वेरिफिकेशन सफल! अब आप 24 घंटे तक फाइलें डाउनलोड कर सकते हैं।")
        return
        
    await message.reply("बोट चालू है! मूवी या फाइल का नाम लिखकर सर्च करें।")

# ऑटो-सर्च (सर्च और थंबनेल सिस्टम)
@app.on_message(filters.text & ~filters.command(["start"]) & filters.user(ADMIN_IDS))
async def auto_search(client, message):
    query = message.text
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=5)
    
    if not files:
        await message.reply("❌ कोई फाइल नहीं मिली।")
        return
        
    for f in files:
        size_mb = round(f.get("file_size", 0) / (1024 * 1024), 2)
        text = f"📂 **{f['name']}**\n💾 **साइज:** {size_mb} MB"
        buttons = [[types.InlineKeyboardButton("📥 फाइल प्राप्त करें", callback_data=str(f['_id']))]]
        
        try:
            if f.get("thumb_id"):
                await client.send_photo(
                    message.chat.id, 
                    f['thumb_id'], 
                    caption=text, 
                    reply_markup=types.InlineKeyboardMarkup(buttons)
                )
            else:
                await message.reply(text, reply_markup=types.InlineKeyboardMarkup(buttons))
        except Exception:
            await message.reply(text, reply_markup=types.InlineKeyboardMarkup(buttons))

# फाइल भेजने वाला सिस्टम (Modified with copy_message and Link Button)
@app.on_callback_query()
async def callback(client, query):
    user_id = query.from_user.id
    
    # वेरिफिकेशन चेक
    if not await is_verified(user_id):
        short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
        buttons = [[types.InlineKeyboardButton("🔗 वेरीफाई करें", url=short_link)]]
        await query.message.reply("⚠️ फाइल पाने के लिए 24 घंटे में एक बार वेरिफिकेशन जरूरी है:", reply_markup=types.InlineKeyboardMarkup(buttons))
        return
    
    file_doc = await get_file_by_id(query.data)
    if not file_doc:
        await query.answer("फाइल मौजूद नहीं है।", show_alert=True)
        return

    # Render variable se link uthane ke liye (ensure VIDEO_LINK config.py mein defined ho)
    link_button = [[types.InlineKeyboardButton("🎥 वीडियो देखने के लिए यहाँ क्लिक करें", url=VIDEO_LINK)]]
    
    status_msg = await query.message.reply("⏳ **फाइल भेजी जा रही है...**")
    
    try:
        # copy_message ka istemal taaki "Forwarded from" tag hat jaye
        sent = await client.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=DATABASE_CHANNEL,
            message_id=file_doc['message_id'],
            reply_markup=types.InlineKeyboardMarkup(link_button)
        )
        await status_msg.delete()
        
        # ऑटो-डिलीट लॉजिक
        await asyncio.sleep(FILE_DELETE_TIME)
        try:
            await sent.delete()
        except Exception:
            pass
            
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await status_msg.edit(f"❌ **एरर:** {str(e)[:50]}")

# ऑटो इंडेक्सिंग
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)

# वेब सर्वर स्टार्ट
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    app.start()
    print("🚀 बोट सफलतापूर्वक ऑनलाइन है!")
    idle()
    
