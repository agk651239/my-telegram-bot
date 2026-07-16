from pyrogram import Client, filters, types
import asyncio, aiohttp, os, time
from config import *
from database import *
from aiohttp import web

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# लॉग भेजने वाला फंक्शन
async def send_log(client, text):
    if LOG_CHANNEL:
        try: await client.send_message(LOG_CHANNEL, text)
        except: pass

# शॉर्टनर लिंक जेनरेटर
async def get_shortlink(url):
    api_url = f"{SHORTENER_WEBSITE}/api?api={SHORTENER_API}&url={url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                data = await response.json()
                return data.get("shortenedUrl", url)
    except: return url

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id) # यूजर को डेटाबेस में रजिस्टर करें
    
    if "verify_" in message.text:
        await set_verify(user_id)
        await message.reply("✅ वेरिफिकेशन सफल! अब आप 24 घंटे तक अनलिमिटेड फाइलें डाउनलोड कर सकते हैं।")
        await send_log(client, f"👤 यूजर वेरीफाई हुआ: {message.from_user.mention} (ID: {user_id})")
        return
    await message.reply("बोट चालू है! फाइल सर्च करने के लिए /search लिखें।")

@app.on_message(filters.command("check") & filters.user(ADMIN_IDS))
async def check_status(client, message):
    try:
        target_id = int(message.text.split(" ")[1])
        user = await get_user_data(target_id)
        if user and user.get("expire_at", 0) > time.time():
            await message.reply(f"✅ यूजर {target_id} अभी वेरीफाइड है।")
        else:
            await message.reply(f"❌ यूजर {target_id} वेरीफाइड नहीं है।")
    except:
        await message.reply("उपयोग: /check [user_id]")

@app.on_message(filters.command("search"))
async def search(client, message):
    query = message.text.replace("/search ", "")
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=10)
    if not files: await message.reply("कोई फाइल नहीं मिली।"); return
    buttons = [[types.InlineKeyboardButton(f['name'], callback_data=f['file_id'])] for f in files]
    await message.reply("फाइलें मिलीं:", reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_callback_query()
async def callback(client, query):
    user_id = query.from_user.id
    if not await is_verified(user_id):
        link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
        await query.message.reply(f"🔗 फाइल पाने के लिए लिंक पर क्लिक करें (24 घंटे में 1 बार):\n{link}")
        return
    
    msg = await client.send_document(query.message.chat.id, query.data)
    await send_log(client, f"📂 फाइल भेजी गई: {query.from_user.mention}")
    
    await asyncio.sleep(FILE_DELETE_TIME)
    try: await msg.delete()
    except: pass

@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_id = message.document.file_id if message.document else message.video.file_id
    await add_file({"name": message.caption or "File", "file_id": file_id})

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
    
