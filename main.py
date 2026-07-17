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

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id)
    
    # 1. यूनिक लिंक (getfile_) हैंडलर
    if "getfile_" in message.text:
        file_id = message.text.split("getfile_")[1]
        
        # फोर्स सबस्क्रिप्शन चेक
        if FORCE_SUB_CHANNEL:
            try:
                await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            except:
                # यहाँ चैनल का नाम या लिंक सही से डालें
                btn = [[types.InlineKeyboardButton("🔗 चैनल जॉइन करें", url=f"https://t.me/{BOT_USERNAME}")]]
                await message.reply("⚠️ **फाइल पाने के लिए पहले चैनल जॉइन करें!**", reply_markup=types.InlineKeyboardMarkup(btn))
                return

        # 24 घंटे का वेरिफिकेशन चेक
        if not await is_verified(user_id):
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
            buttons = [[types.InlineKeyboardButton("🔗 वेरीफाई करें (24 घंटे)", url=short_link)]]
            await message.reply("⚠️ **फाइल पाने के लिए 24 घंटे में एक बार वेरिफिकेशन जरूरी है:**", reply_markup=types.InlineKeyboardMarkup(buttons))
            return
        
        # फाइल भेजें
        file_doc = await get_file_by_id(file_id)
        if file_doc:
            try:
                # यहाँ हमने ID को int में बदल दिया है ताकि कोई एरर न आए
                await client.copy_message(
                    chat_id=message.chat.id, 
                    from_chat_id=DATABASE_CHANNEL, 
                    message_id=int(file_doc['message_id'])
                )
            except Exception as e:
                await message.reply(f"❌ फाइल भेजने में एरर आया: {e}")
        else:
            await message.reply("❌ फाइल डेटाबेस में मौजूद नहीं है।")
        return

    # वेरिफिकेशन सक्सेस कमांड
    if "verify_" in message.text:
        await set_verify(user_id)
        await message.reply("✅ **वेरिफिकेशन सफल!** अब आप 24 घंटे तक फाइलें डाउनलोड कर सकते हैं।")
        return
        
    await message.reply("बोट चालू है! सर्च करने के लिए एडमिन को मैसेज करें या फाइल सर्च करें।")

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

# ऑटो इंडेक्सिंग
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        try:
            await client.send_message(LOG_CHANNEL, f"✅ **सफलतापूर्वक इंडेक्स हुआ:**\n📂 {file_info['name']}")
        except: pass

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
    try: app.send_message(LOG_CHANNEL, "🚀 **बोट ऑनलाइन है!**")
    except: pass
    idle()
    
