from pyrogram import Client, filters, types
import asyncio, aiohttp, time
from bson import ObjectId
from config import *
from database import *
from helpers import *  # आपका helpers.py
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
    await message.reply("बोट चालू है! एडमिन द्वारा दिए गए लिंक पर क्लिक करें।")

# सर्च कमांड: सिर्फ एडमिन के लिए, 50% मैचिंग और थंबनेल के साथ
@app.on_message(filters.command("search") & filters.user(ADMIN_IDS))
async def search(client, message):
    query = message.text.replace("/search ", "")
    # $regex 50% मैचिंग के लिए बेहतर है
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=10)
    
    if not files: await message.reply("कोई फाइल नहीं मिली।"); return
    
    for f in files:
        size_mb = round(f.get("file_size", 0) / (1024 * 1024), 2)
        text = f"📂 **नाम:** {f['name']}\n💾 **साइज:** {size_mb} MB\n🆔 **ID:** `{f['_id']}`"
        buttons = [[types.InlineKeyboardButton("📥 फाइल प्राप्त करें", callback_data=str(f['_id']))]]
        
        if f.get("thumb_id"):
            await client.send_photo(message.chat.id, f['thumb_id'], caption=text, reply_markup=types.InlineKeyboardMarkup(buttons))
        else:
            await message.reply(text, reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_callback_query()
async def callback(client, query):
    user_id = query.from_user.id
    
    # वेरिफिकेशन चेक: अगर यूजर 24 घंटे में वेरीफाई नहीं है, तो लिंक दें
    if not await is_verified(user_id):
        short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
        buttons = [[types.InlineKeyboardButton("🔗 फाइल पाने के लिए वेरीफाई करें", url=short_link)]]
        await query.message.reply("⚠️ फाइल पाने के लिए 24 घंटे में एक बार वेरिफिकेशन जरूरी है:", reply_markup=types.InlineKeyboardMarkup(buttons))
        return
    
    # अगर वेरीफाइड है, तो सीधे फाइल भेजें
    file_doc = await get_file_by_id(query.data)
    if file_doc:
        msg = await client.send_document(query.message.chat.id, file_doc['file_id'])
        await asyncio.sleep(FILE_DELETE_TIME)
        try: await msg.delete()
        except: pass
    else:
        await query.answer("फाइल मौजूद नहीं है।", show_alert=True)

@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    # इंडेक्सिंग के समय फाइल साइज और थंबनेल को सेव करें
    media = message.document or message.video
    file_info = {
        "name": message.caption or media.file_name or "File",
        "file_id": media.file_id,
        "file_size": media.file_size,
        "thumb_id": media.thumbs[0].file_id if media.thumbs else None
    }
    await add_file(file_info)

async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    app.run()
    
