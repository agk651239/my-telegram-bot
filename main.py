import asyncio
from pyrogram import Client, filters
from aiohttp import web
from config import *
from database import *

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Render Health Check
async def handle(request): return web.Response(text="Bot is running")

@app.on_message(filters.chat(DATABASE_CHANNEL) & filters.media)
async def index_files(client, message):
    file_info = {
        "file_id": message.document.file_id if message.document else message.video.file_id,
        "name": message.caption or "File",
        "size": message.video.file_size if message.video else message.document.file_size
    }
    await add_file(file_info)
    await client.send_message(LOG_CHANNEL, f"✅ Indexed: {file_info['name']}")

@app.on_message(filters.command("search"))
async def search(client, message):
    if message.from_user.id not in ADMIN_IDS: return
    # Search logic...
    await message.reply("Admin Search Ready")

@app.on_message(filters.command("start"))
async def start(client, message):
    if await is_verified(message.from_user.id):
        await message.reply("Welcome! You are verified.")
    else:
        await message.reply(f"Please Verify: {SHORTENER_WEBSITE}/verify?token={message.from_user.id}")

async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', handle)
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 10000).start()

loop = asyncio.get_event_loop()
loop.create_task(start_web())
app.run()

