import asyncio
from pyrogram import Client, filters
from aiohttp import web
from config import *
from database import *
from helpers import get_shortlink, get_file_info

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 1. Render Health Check (ताकि बोट न सोए)
async def handle(request): return web.Response(text="Bot is running")

# 2. Start Command - वेरिफिकेशन चेक करना
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    if await is_verified(user_id):
        await message.reply("आप पहले से वेरीफाइड हैं। सर्च करें!")
    else:
        link = get_shortlink(user_id)
        await message.reply(f"❌ Verification Required!\nकृपया लिंक ओपन करके वेरीफाई करें:\n{link}")

# 3. Database Channel से फाइल Index करना
@app.on_message(filters.chat(DATABASE_CHANNEL) & filters.media)
async def index_files(client, message):
    name, size = get_file_info(message)
    file_info = {
        "file_id": message.document.file_id if message.document else message.video.file_id,
        "name": name,
        "size": size
    }
    await add_file(file_info)
    await client.send_message(LOG_CHANNEL, f"✅ Indexed: {name} ({size})")

# 4. Search Command (Admin Only)
@app.on_message(filters.command("search"))
async def search(client, message):
    if message.from_user.id not in ADMIN_IDS: return
    await message.reply("Admin Search Ready. फाइल का नाम बताएं...")

# 5. Web Server Start
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', handle)
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()

loop = asyncio.get_event_loop()
loop.create_task(start_web())
app.run()
