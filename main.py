from pyrogram import Client, filters, types
import asyncio, aiohttp, time
from bson import ObjectId
from config import *
from database import *
from helpers import *
from aiohttp import web

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def send_log(client, text):
    if LOG_CHANNEL:
        try: await client.send_message(LOG_CHANNEL, text)
        except: pass

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id)
    if "verify_" in message.text:
        await set_verify(user_id)
        await message.reply("✅ वेरिफिकेशन सफल! अब आप 24 घंटे तक फाइलें डाउनलोड कर सकते हैं।")
        await send_log(client, f"👤 यूजर वेरीफाई हुआ: {message.from_user.mention}")
        return
    await message.reply("बोट चालू है! मूवी या फाइल का नाम लिखकर सर्च करें।")

# ऑटो सर्च (बिना किसी कमांड के, सिर्फ एडमिन के लिए)
@app.on_message(filters.text & ~filters.command(["start", "check", "search"]) & filters.user(ADMIN_IDS))
async def auto_search(client, message):
    query = message.text
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=5)
    
    if not files: 
        await message.reply("❌ कोई फाइल नहीं मिली।")
        return
    
    for f in files:
        size_mb = round(f.get("file_size", 0) / (1024 * 1024), 2)
        text = f"📂 **नाम:** {f['name']}\n💾 **साइज:** {size_mb} MB"
        buttons = [[types.InlineKeyboardButton("📥 फाइल प्राप्त करें", callback_data=str(f['_id']))]]
        
        if f.get("thumb_id"):
            await client.send_photo(message.chat.id, f['thumb_id'], caption=text, reply_markup=types.InlineKeyboardMarkup(buttons))
        else:
            await message.reply(text, reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_callback_query()
async def callback(client, query):
    user_id = query.from_user.id
    
    if not await is_verified(user_id):
        short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
        buttons = [[types.InlineKeyboardButton("🔗 वेरीफाई करें", url=short_link)]]
        await query.message.reply("⚠️ फाइल पाने के लिए 24 घंटे में एक बार वेरिफिकेशन जरूरी है:", reply_markup=types.InlineKeyboardMarkup(buttons))
        return
    
    file_doc = await get_file_by_id(query.data)
    if not file_doc:
        await query.answer("फाइल मौजूद नहीं है।", show_alert=True)
        return

    # स्टेटस मैसेज
    status_msg = await query.message.reply("⏳ **फाइल आ रही है, कृपया प्रतीक्षा करें...**")
    
    # फाइल भेजने का लॉजिक (thumb_id के आधार पर वीडियो या डॉक्यूमेंट पहचानें)
    try:
        if file_doc.get("thumb_id"):
            msg = await client.send_video(query.message.chat.id, file_doc['file_id'])
            await status_msg.edit("✅ **वीडियो सफलतापूर्वक भेजा गया!**")
        else:
            msg = await client.send_document(query.message.chat.id, file_doc['file_id'])
            await status_msg.edit("✅ **डॉक्यूमेंट सफलतापूर्वक भेजा गया!**")
    except Exception as e:
        await status_msg.edit(f"❌ **फाइल भेजने में एरर आया:** {str(e)[:50]}")
        return
            
    # डिलीट टाइमर
    await asyncio.sleep(FILE_DELETE_TIME)
    try: 
        await msg.delete()
        await status_msg.delete()
    except: pass

@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        # फाइल इंडेक्सिंग का लॉग
        log_text = f"✅ **नई फाइल इंडेक्स हुई:**\n📂 **नाम:** {file_info['name']}\n💾 **साइज:** {round(file_info['file_size'] / (1024 * 1024), 2)} MB"
        await send_log(client, log_text)

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
    # बोट ऑनलाइन का लॉग
    loop.run_until_complete(create_indexes()) # इंडेक्सिंग शुरू करें
    loop.run_until_complete(send_log(app, "🚀 **बोट सफलतापूर्वक ऑनलाइन हो गया है!**"))
    app.idle()
    
