from pyrogram import Client, filters, types
import asyncio
from aiohttp import web
from config import *
from database import *
from helpers import get_shortlink, get_file_info

# बोट क्लाइंट सेटअप
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Force Subscribe Check
async def is_subscribed(client, user_id):
    if not FORCE_SUB_CHANNEL: return True
    try:
        await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return True
    except: return False

@app.on_message(filters.command("start"))
async def start(client, message):
    if "verify_" in message.text:
        await set_verify(message.from_user.id)
        await message.reply("✅ वेरिफिकेशन सफल!")
        return
    await message.reply("बोट चालू है! सर्च करने के लिए /search लिखें।")

@app.on_message(filters.command("search"))
async def search(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(client, user_id):
        await message.reply(f"❌ पहले चैनल ज्वाइन करें: {FORCE_SUB_CHANNEL}")
        return
    
    query = message.text.replace("/search ", "")
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=10)
    
    if not files: 
        await message.reply("कोई फाइल नहीं मिली।")
        return
    
    buttons = [[types.InlineKeyboardButton(f['name'], callback_data=f['file_id'])] for f in files]
    await message.reply("फाइलें मिलीं:", reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_callback_query()
async def callback(client, query):
    await client.send_document(query.message.chat.id, query.data)

# फाइल इंडेक्सिंग फंक्शन (यह चैनल से फाइल सेव करेगा)
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video))
async def index_files(client, message):
    file_id = message.document.file_id if message.document else message.video.file_id
    file_name = message.caption or (message.document.file_name if message.document else "Unknown_File")
    
    # डेटाबेस में सेव करें
    await db.files.insert_one({"name": file_name, "file_id": file_id})
    print(f"✅ नई फाइल सेव हुई: {file_name}")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast(client, message):
    users = await get_all_users()
    msg = message.text.replace("/broadcast ", "")
    async for user in users:
        try: await client.send_message(user['user_id'], msg)
        except: pass
    await message.reply("✅ ब्रॉडकास्ट पूरा हुआ।")

# वेब सर्वर
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()
    print("Web Server started on port 10000")

async def ping_server():
    while True:
        await asyncio.sleep(300)
        print("Bot is alive...")

# मुख्य स्टार्टअप
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    loop.create_task(ping_server())
    print("Starting Telegram Bot...")
    app.run()
    
