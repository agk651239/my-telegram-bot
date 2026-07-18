from pyrogram import Client, filters, types, idle
import asyncio
import aiohttp
import logging
from config import *
from database import * 
from helpers import *
from aiohttp import web

# बोट क्लाइंट सेटअप
app = Client(
    "bot_session", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

# --- फंक्शन: मैसेज ऑटो-डिलीट ---
async def delete_after_delay(message, delay):
    if delay <= 0: return # अगर delay 0 या कम है, तो डिलीट न करें
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

# --- सुधरा हुआ: Keep Alive (Ping Error 404 फिक्स) ---
async def keep_alive():
    """स्वयं को पिंग करें ताकि Render स्लीप न हो।"""
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(60) # हर 1 मिनट में
            try:
                # सीधे localhost पिंग करें, क्योंकि वेब सर्वर यहीं चल रहा है
                async with session.get("http://localhost:" + str(PORT)) as resp:
                    logging.info(f"Pinged server, status: {resp.status}")
            except Exception as e:
                logging.error(f"❌ Ping Failed: {e}")

# --- 1. ब्रॉडकास्ट कमांड ---
@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast_handler(client, message):
    if not message.reply_to_message:
        return await message.reply("❌ कृपया उस मैसेज को रिप्लाई करें जिसे ब्रॉडकास्ट करना है।")
    users = await db.users.find({}).to_list(length=None)
    success = 0
    for user in users:
        try:
            await client.copy_message(user["user_id"], message.chat.id, message.reply_to_message.id)
            success += 1
            await asyncio.sleep(0.05) 
        except: pass
    await message.reply(f"✅ मैसेज {success} यूजर्स को भेज दिया गया।")

# --- 5. टोटल यूजर्स स्टेटस ---
@app.on_message(filters.command("stats") & filters.user(ADMIN_IDS))
async def stats_handler(client, message):
    total_users = await db.users.count_documents({})
    await message.reply(f"📊 **बोट के कुल यूजर्स:** {total_users}")

@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    is_user_exist = await db.users.find_one({"user_id": user_id})
    if not is_user_exist:
        await add_user(user_id)
        try: await client.send_message(LOG_CHANNEL, f"👤 **नया यूजर:** `{user_id}`")
        except: pass
    
    command = message.text.split(" ", 1)
    
    if len(command) > 1 and "verify_" in command[1]:
        await set_verify(user_id)
        await message.reply("✅ **Verification successful!** Please click on the video link again to download your file.\nवेरिफिकेशन सफल रहा! कृपया फाइल डाउनलोड करने के लिए वीडियो लिंक पर दोबारा क्लिक करें।")
        return

    if len(command) > 1 and "getfile_" in command[1]:
        file_id = command[1].split("getfile_")[1]
        
        if FORCE_SUB_CHANNEL:
            try: await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            except:
                btn = [[types.InlineKeyboardButton("🔗 चैनल जॉइन करें", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('-100', '')}")]]
                await message.reply("⚠️ **पहले चैनल जॉइन करें!**", reply_markup=types.InlineKeyboardMarkup(btn))
                return

        if user_id not in ADMIN_IDS and not await is_verified(user_id):
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}")
            buttons = [[types.InlineKeyboardButton("🔗 वेरीफाई करें", url=short_link)]]
            await message.reply("⚠️ **Verify once to get unlimited file access for the next 24 hours!**\nवेरिफिकेशन पूरा करें और अगले 24 घंटों तक असीमित (Unlimited) फाइलें डाउनलोड करें!", reply_markup=types.InlineKeyboardMarkup(buttons))
            return
        
        file_doc = await get_file_by_id(file_id)
        if file_doc:
            try:
                sent_msg = await client.copy_message(message.chat.id, DATABASE_CHANNEL, int(file_doc['message_id']))
                # यदि ऑटो-डिलीट नहीं चाहिए, तो AUTO_DELETE_TIME को 0 रखें
                asyncio.create_task(delete_after_delay(sent_msg, AUTO_DELETE_TIME))
            except Exception as e:
                await message.reply(f"❌ एरर: {e}")
        return
        
    await message.reply("बोट चालू है! सर्च करने के लिए फाइल का नाम लिखें।")

# --- फाइल इंडेक्सिंग ---
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video | filters.photo))
async def index_files(client, message):
    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        try:
            await client.send_message(LOG_CHANNEL, f"✅ **इंडेक्स हुआ:**\n📂 {file_info['name']}")
        except Exception as e:
            logging.error(f"Log Channel Error: {e}")

@app.on_message(filters.text & ~filters.command(["start", "broadcast", "stats"]) & filters.user(ADMIN_IDS))
async def auto_search(client, message):
    query = message.text
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=5)
    if not files: return await message.reply("❌ कोई फाइल नहीं मिली।")
    for f in files:
        unique_link = f"https://t.me/{BOT_USERNAME}?start=getfile_{f['_id']}"
        await message.reply(f"📂 **{f['name']}**\n🔗 `{unique_link}`")

async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(PORT)).start()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(create_indexes())
    loop.create_task(start_web())
    loop.create_task(keep_alive())
    app.start()
    try: app.send_message(LOG_CHANNEL, "🚀 **बोट स्टार्ट हो गया है!**")
    except: pass
    idle()
    
