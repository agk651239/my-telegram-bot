from pyrogram import Client, filters, types, idle
from pyrogram.errors import FloodWait
import asyncio
import logging
from config import *
from database import *
from helpers import *
from aiohttp import web

# बोट का क्लाइंट सेटअप
app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 1. स्टार्ट कमांड (Verification Logic + Unique Link Handler)
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id)
    
    # यदि लिंक में फाइल आईडी है
    if "getfile_" in message.text:
        file_id = message.text.split("getfile_")[1]
        
        # वेरिफिकेशन चेक (Shortener के साथ)
        if not await is_verified(user_id):
            verify_url = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
            short_link = await get_shortlink(verify_url)
            buttons = [[types.InlineKeyboardButton("🔗 वेरीफाई करें (Shortener)", url=short_link)]]
            await message.reply(
                "⚠️ **वीडियो प्राप्त करने के लिए पहले वेरीफाई करें!**\n\n"
                "वेरिफिकेशन केवल **24 घंटे** के लिए मान्य होता है।", 
                reply_markup=types.InlineKeyboardMarkup(buttons)
            )
            return
        
        # यदि वेरीफाइड है, तो सीधे फाइल भेजें
        file_doc = await get_file_by_id(file_id)
        if file_doc:
            await client.copy_message(message.chat.id, DATABASE_CHANNEL, file_doc['message_id'])
        else:
            await message.reply("❌ फाइल मौजूद नहीं है।")
        return

    # वेरिफिकेशन सक्सेस हैंडलर
    if "verify_" in message.text:
        await set_verify(user_id)
        await message.reply(
            "✅ **वेरिफिकेशन सफल!**\n\n"
            "अब आप अगले **24 घंटों** तक किसी भी फाइल का डायरेक्ट लिंक इस्तेमाल कर सकते हैं।\n"
            "समय पूरा होने के बाद आपको दोबारा वेरीफाई करना होगा।"
        )
        return
        
    await message.reply("बोट चालू है! मूवी या फाइल का नाम लिखकर सर्च करें।")

# 2. ऑटो-सर्च (Admin के लिए Unique Link Generator)
@app.on_message(filters.text & ~filters.command(["start"]) & filters.user(ADMIN_IDS))
async def auto_search(client, message):
    query = message.text
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=5)
    
    if not files:
        await message.reply("❌ कोई फाइल नहीं मिली।")
        return
        
    for f in files:
        size_mb = round(f.get("file_size", 0) / (1024 * 1024), 2)
        unique_link = f"https://t.me/{BOT_USERNAME}?start=getfile_{f['_id']}"
        text = f"📂 **{f['name']}**\n💾 **साइज:** {size_mb} MB\n\n🔗 **डायरेक्ट लिंक:** `{unique_link}`"
        
        await message.reply(text)

# 3. ऑटो इंडेक्सिंग (फाइल अपलोड नोटिफिकेशन के साथ)
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        # अपलोड सक्सेस नोटिफिकेशन
        try:
            await client.send_message(
                LOG_CHANNEL, 
                f"✅ **फाइल/वीडियो सफलतापूर्वक अपलोड हो गई!**\n\n"
                f"📂 **नाम:** {file_info['name']}\n"
                f"💾 **साइज:** {round(file_info['file_size']/(1024*1024), 2)} MB"
            )
        except Exception as e:
            print(f"Log Error: {e}")

# 4. वेब सर्वर और स्टार्ट अप नोटिफिकेशन
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
    
    # बोट स्टार्ट नोटिफिकेशन
    try:
        app.send_message(LOG_CHANNEL, "🚀 **बोट सफलतापूर्वक स्टार्ट हो गया है!**\n\n✅ बोट कनेक्टेड और रनिंग है।")
    except:
        pass
        
    print("🚀 बोट सफलतापूर्वक ऑनलाइन है!")
    idle()
    
