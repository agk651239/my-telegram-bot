import asyncio
from pyrogram import Client, filters
from aiohttp import web
from config import *
from database import *
from helpers import get_shortlink, get_file_info

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def handle(request): return web.Response(text="Bot is running")

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS or await is_verified(user_id):
        await message.reply("स्वागत है! आप सर्च कर सकते हैं।")
    else:
        link = get_shortlink(user_id)
        await message.reply(f"❌ वेरिफिकेशन जरूरी है:\n{link}")

@app.on_message(filters.chat(DATABASE_CHANNEL) & filters.media)
async def index_files(client, message):
    name, size = get_file_info(message)
    await add_file({"name": name, "size": size, "file_id": message.document.file_id if message.document else message.video.file_id})
    await client.send_message(LOG_CHANNEL, f"✅ Indexed: {name}")

# Web server for Render
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', handle)
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()

loop = asyncio.get_event_loop()
loop.create_task(start_web())
app.run()
