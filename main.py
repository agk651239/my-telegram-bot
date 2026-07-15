from pyrogram import Client, filters, types
import asyncio, aiohttp
from config import *
from database import *

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
    if "verify_" in message.text:
        await set_verify(message.from_user.id)
        await message.reply("✅ वेरिफिकेशन सफल! अब आप 24 घंटे तक फाइलें डाउनलोड कर सकते हैं।")
        return
    await message.reply("बोट चालू है! सर्च करने के लिए /search लिखें।")

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
        await query.message.reply(f"🔗 फाइल पाने के लिए लिंक पर क्लिक करें (24 घंटे में एक बार):\n{link}")
        return
    
    msg = await client.send_document(query.message.chat.id, query.data)
    await query.message.reply("⚠️ यह फाइल 1 घंटे में डिलीट हो जाएगी।")
    await asyncio.sleep(FILE_DELETE_TIME)
    try: await msg.delete()
    except: pass

@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    name = message.caption or (message.document.file_name if message.document else "Unknown")
    file_id = message.document.file_id if message.document else message.video.file_id
    await add_file({"name": name, "file_id": file_id})

if __name__ == "__main__":
    app.run()
    
