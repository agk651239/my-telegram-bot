from pyrogram import Client, filters, types, idle
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

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id)
    
    # कमांड को अलग करना (getfile_ या verify_ के लिए)
    command = message.text.split(" ", 1)
    
    # 1. वेरिफिकेशन सक्सेस हैंडलर
    if len(command) > 1 and "verify_" in command[1]:
        await set_verify(user_id)
        await message.reply("✅ **वेरिफिकेशन सफल!** अब आप 24 घंटे तक फाइलें डाउनलोड कर सकते हैं।")
        return

    # 2. फाइल रिक्वेस्ट (getfile_) हैंडलर
    if len(command) > 1 and "getfile_" in command[1]:
        file_id = command[1].split("getfile_")[1]
        
        # फोर्स सबस्क्रिप्शन चेक
        if FORCE_SUB_CHANNEL:
            try:
                await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            except:
                # चैनल लिंक को सही फॉर्मेट में रखें
                btn = [[types.InlineKeyboardButton("🔗 चैनल जॉइन करें", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('-100', '')}")]]
                await message.reply("⚠️ **फाइल पाने के लिए पहले चैनल जॉइन करें!**", reply_markup=types.InlineKeyboardMarkup(btn))
                return

        # वेरिफिकेशन चेक (एडमिन को छोड़कर)
        if user_id not in ADMIN_IDS and not await is_verified(user_id):
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
            buttons = [[types.InlineKeyboardButton("🔗 वेरीफाई करें (24 घंटे)", url=short_link)]]
            await message.reply("⚠️ **फाइल पाने के लिए 24 घंटे में एक बार वेरिफिकेशन जरूरी है:**", reply_markup=types.InlineKeyboardMarkup(buttons))
            return
        
        # फाइल कॉपी करें
        file_doc = await get_file_by_id(file_id)
        if file_doc and file_doc.get("message_id"):
            try:
                await client.copy_message(
                    chat_id=message.chat.id, 
                    from_chat_id=DATABASE_CHANNEL, 
                    message_id=int(file_doc['message_id'])
                )
            except Exception as e:
                await message.reply(f"❌ फाइल भेजने में एरर: {e}")
        else:
            await message.reply("❌ फाइल डेटाबेस में मौजूद नहीं है।")
        return
        
    await message.reply("बोट चालू है! सर्च करने के लिए फाइल का नाम लिखें।")

# ऑटो-सर्च (Admin)
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
        text = f"📂 **{f['name']}**\n💾 **साइज:** {size_mb} MB\n\n🔗 **लिंक:** `{unique_link}`"
        await message.reply(text)

# ऑटो इंडेक्सिंग (DATABASE_CHANNEL से)
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        try:
            await client.send_message(LOG_CHANNEL, f"✅ **इंडेक्स हुआ:**\n📂 {file_info['name']}")
        except: pass

async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # डेटाबेस इंडेक्स एक बार बनाना जरूरी है
    loop.run_until_complete(create_indexes())
    # वेब सर्वर
    loop.create_task(start_web())
    # बोट स्टार्ट
    app.start()
    try: app.send_message(LOG_CHANNEL, "🚀 **बोट ऑनलाइन है!**")
    except: pass
    idle()
    
