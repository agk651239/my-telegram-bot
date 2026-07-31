from pyrogram import Client, filters, types, idle
from pyrogram.errors import UserIsBlocked, InputUserDeactivated
import asyncio
import aiohttp
import logging
import secrets
from humanfriendly import format_size
from config import *
from database import * 
from helpers import *
from aiohttp import web

# लॉगिंग सेटअप
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# बोट क्लाइंट सेटअप
app = Client(
    "bot_session", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    in_memory=True 
)

# एल्बम प्रोसेसिंग के लिए सेट
processed_albums = set()

# --- फंक्शन: मैसेज ऑटो-डिलीट (3600 सेकंड = 1 घंटा) ---
async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

# --- फंक्शन: एल्बम ऑटो-डिलीट ---
async def delete_album_after_delay(messages, warn_msg, delay):
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await app.delete_messages(msg.chat.id, msg.id)
        except Exception:
            pass
    try:
        await warn_msg.delete()
    except Exception:
        pass

# --- प्रीमियम स्टेबिलिटी (वेब-सर्वर SSL सपोर्ट के साथ) ---
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running"))
    
    protocol = "https" if HAS_SSL else "http"
    logging.info(f"🌐 वेब-सर्वर {protocol}://0.0.0.0:{PORT} पर शुरू हो रहा है।")
    
    runner = web.AppRunner(app_web)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(PORT)).start()

async def keep_alive():
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(60)
            try:
                protocol = "https" if HAS_SSL else "http"
                async with session.get(f"{protocol}://localhost:{PORT}") as resp:
                    logging.info(f"Pinged server, status: {resp.status}")
            except Exception as e:
                logging.error(f"❌ Ping Failed: {e}")

# --- बैकग्राउंड टास्क: डेली रिपोर्ट (हर 24 घंटे में) ---
async def send_daily_report():
    while True:
        await asyncio.sleep(86400) # 24 घंटे
        try:
            total_users = await db.users.count_documents({})
            total_files = await db.files.count_documents({})
            report_text = (
                f"📅 **Daily Report**\n\n"
                f"📊 **Total Users:** `{total_users}`\n"
                f"📂 **Total Files Indexed:** `{total_files}`\n"
                f"🟢 **Bot Status:** Online & Running"
            )
            await app.send_message(LOG_CHANNEL, report_text)
        except Exception as e:
            logging.error(f"Daily Report Error: {e}")

# --- 1. ब्रॉडकास्ट कमांड ---
@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast_handler(client, message):
    if not message.reply_to_message:
        return await message.reply("❌ कृपया मैसेज रिप्लाई करें।")
    users = await db.users.find({}).to_list(length=None)
    success = 0
    blocked = 0
    for user in users:
        try:
            await client.copy_message(user["user_id"], message.chat.id, message.reply_to_message.id)
            success += 1
            await asyncio.sleep(0.05) 
        except (UserIsBlocked, InputUserDeactivated):
            blocked += 1
            # 🚫 User Blocked Bot Log
            try:
                await client.send_message(LOG_CHANNEL, f"🚫 **User Blocked Bot:** `{user['user_id']}`")
            except: pass
        except: 
            pass
    await message.reply(f"✅ मैसेज {success} यूजर्स को भेज दिया गया। (ब्लॉक किए गए: {blocked})")

# --- 2. स्टेटस कमांड (Advanced /stats) ---
@app.on_message(filters.command("stats") & filters.user(ADMIN_IDS))
async def stats_handler(client, message):
    total_users = await db.users.count_documents({})
    total_files = await db.files.count_documents({})
    verified_users = await db.users.count_documents({"is_verified": True})
    
    stats_text = (
        f"📊 **Advanced Bot Statistics (/stats)**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"✅ **Verified Users:** `{verified_users}`\n"
        f"📂 **Total Indexed Files:** `{total_files}`\n"
        f"🟢 **Bot Status:** Active"
    )
    await message.reply(stats_text)
    try:
        await client.send_message(LOG_CHANNEL, f"📊 **Advanced /stats checked by Admin:** `{message.from_user.id}`")
    except: pass

# --- 3. स्टार्ट कमांड (एंटी-बायपास + एडवांस्ड लॉग्स) ---
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    
    if not await db.users.find_one({"user_id": user_id}):
        await add_user(user_id)
        total_users = await db.users.count_documents({})
        try: 
            # 🆕 New User Joined + Total Users Log
            await client.send_message(
                LOG_CHANNEL, 
                f"🆕 **New User Joined:** `{user_id}`\n📊 **Total Users:** `{total_users}`"
            )
        except: pass
    
    command = message.text.split(" ", 1)
    
    if len(command) > 1 and "verify_" in command[1]:
        try:
            parts = command[1].split("_")
            if len(parts) >= 3:
                token_in_link = parts[2]
                user_data = await db.users.find_one({"user_id": user_id})
                
                saved_token = user_data.get("verify_token") if user_data else None
                token_used = user_data.get("token_used", False)
                
                if not saved_token or saved_token != token_in_link or token_used:
                    return await message.reply(
                        "❌ **यह वेरिफिकेशन लिंक एक्सपायर हो चुका है या पहले ही इस्तेमाल किया जा चुका है!**\n\n"
                        "कृपया फाइल लिंक पर दोबारा क्लिक करके नया शॉर्टलिंक जनरेट करें।"
                    )
                
                await db.users.update_one({"user_id": user_id}, {"$set": {"token_used": True}})
        except Exception as e:
            logging.error(f"Token Verification Error: {e}")

        await set_verify(user_id)
        
        # ✅ Verification Completed Log
        try:
            await client.send_message(LOG_CHANNEL, f"✅ **Verification Completed:** `{user_id}`")
        except: pass

        await message.reply(
            "✅ **Verification successful!**\n\n"
            "**Please click on your File or Album link again to download.**\n\n"
            "वेरिफिकेशन सफल रहा!\n"
            "कृपया File या Album डाउनलोड करने के लिए लिंक पर दोबारा क्लिक करें。"
        )
        return

    if len(command) > 1 and "getfile_" in command[1]:
        file_id = command[1].split("getfile_")[1]
        
        if FORCE_SUB_CHANNEL:
            try: await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            except:
                btn = [[types.InlineKeyboardButton("🔗 चैनल जॉइन करें / Join Channel", url=f"https://t.me/{str(FORCE_SUB_CHANNEL).replace('-100', '')}")]]
                await message.reply("⚠️ **पहले चैनल जॉइन करें! / Please join the channel first!**", reply_markup=types.InlineKeyboardMarkup(btn))
                return

        if user_id not in ADMIN_IDS and not await is_verified(user_id):
            unique_token = secrets.token_hex(6)
            await db.users.update_one(
                {"user_id": user_id}, 
                {"$set": {"verify_token": unique_token, "token_used": False}}
            )
            
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}_{unique_token}")
            
            # ⚠️ Verification Pending Log
            try:
                await client.send_message(LOG_CHANNEL, f"⚠️ **Verification Pending:** `{user_id}` requested file.")
            except: pass

            buttons = [
                [types.InlineKeyboardButton("🔗 वेरीफाई करें / Verify Now", url=short_link)],
                [types.InlineKeyboardButton("❓ वेरिफिकेशन कैसे करें? / How to Verify?", url="https://t.me/YourTutorialChannel")]
            ]
            await message.reply(
                "⚠️ **Verify once to get unlimited File & Album access for the next 24 hours!**\n\n"
                "एक बार वेरिफाई करें और अगले 24 घंटे तक सभी Files और Albums डाउनलोड करें।",
                reply_markup=types.InlineKeyboardMarkup(buttons)
            )
            return
        
        file_doc = await get_file_by_id(file_id)
        if file_doc:
            try:
                sent_msg = await client.copy_message(message.chat.id, DATABASE_CHANNEL, int(file_doc['message_id']))
                warn_msg = await message.reply(
                    "⚠️ **आपकी फाइल 1 घंटे में अपने आप डिलीट हो जाएगी। कृपया इसे अभी सेव कर लें!**\n\n"
                    "**Your file will be deleted automatically in 1 hour. Please save it now!**"
                )
                asyncio.create_task(delete_after_delay(sent_msg, 3600))
                asyncio.create_task(delete_after_delay(warn_msg, 3600))
            except Exception as e:
                await message.reply(f"❌ एरर: {e}")
        return
    
    if len(command) > 1 and "getalbum_" in command[1]:
        if FORCE_SUB_CHANNEL:
            try: await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            except:
                btn = [[types.InlineKeyboardButton("🔗 चैनल जॉइन करें / Join Channel", url=f"https://t.me/{str(FORCE_SUB_CHANNEL).replace('-100', '')}")]]
                await message.reply("⚠️ **पहले चैनल जॉइन करें! / Please join the channel first!**", reply_markup=types.InlineKeyboardMarkup(btn))
                return

        if user_id not in ADMIN_IDS and not await is_verified(user_id):
            unique_token = secrets.token_hex(6)
            await db.users.update_one(
                {"user_id": user_id}, 
                {"$set": {"verify_token": unique_token, "token_used": False}}
            )
            
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}_{unique_token}")
            
            # ⚠️ Verification Pending Log
            try:
                await client.send_message(LOG_CHANNEL, f"⚠️ **Verification Pending:** `{user_id}` requested album.")
            except: pass

            buttons = [
                [types.InlineKeyboardButton("🔗 वेरीफाई करें / Verify Now", url=short_link)],
                [types.InlineKeyboardButton("❓ वेरिफिकेशन कैसे करें? / How to Verify?", url="https://t.me/YourTutorialChannel")]
            ]
            await message.reply(
                "⚠️ **Verify once to get unlimited File & Album access for the next 24 hours!**\n\n"
                "एक बार वेरिफाई करें और अगले 24 घंटे तक सभी Files और Albums डाउनलोड करें।",
                reply_markup=types.InlineKeyboardMarkup(buttons)
            )
            return

        group_id = int(command[1].split("getalbum_")[1])

        all_files = await db.files.find(
            {"media_group_id": group_id}
        ).sort("message_id", 1).to_list(length=None)

        if not all_files:
            return await message.reply("❌ Album नहीं मिला।")

        media_group = []
        for f in all_files:
            if f["file_type"] == "photo":
                media_group.append(types.InputMediaPhoto(media=f["file_id"]))
            elif f["file_type"] == "video":
                media_group.append(types.InputMediaVideo(media=f["file_id"]))
        
        if not media_group:
            return await message.reply("❌ Album में कोई Video या Photo नहीं मिला।")

        sent_msgs = await client.send_media_group(
            chat_id=message.chat.id,
            media=media_group
        )
        warn_msg = await message.reply(
            "⚠️ **आपकी फाइल 1 घंटे में अपने आप डिलीट हो जाएगी। कृपया इसे अभी सेव कर लें!**\n\n"
            "**Your file will be deleted automatically in 1 hour. Please save it now!**"
        )
        asyncio.create_task(delete_album_after_delay(sent_msgs, warn_msg, 3600))
        return
        
    await message.reply("बोट चालू है! सर्च करने के लिए फाइल का नाम लिखें।\nBot is active! Send file name to search.")

# --- 4. फाइल इंडेक्सिंग ---
@app.on_message(filters.chat(DATABASE_CHANNEL) & (filters.document | filters.video | filters.photo))
async def index_files(client, message):
    if message.media_group_id:
        if message.media_group_id in processed_albums:
            return
        processed_albums.add(message.media_group_id)
        await asyncio.sleep(2)
        try:
            media_group = await client.get_media_group(message.chat.id, message.id)
            caption = None
            for m in media_group:
                if m.caption:
                    caption = m.caption
                    break
            for m in media_group:
                if caption:
                    m.caption = caption
                file_info = await get_file_info(m)
                if file_info:
                    file_info["media_group_id"] = message.media_group_id
                    await add_file(file_info)
            
            # 🎞️ Album Upload Successfully Log
            try:
                await client.send_message(LOG_CHANNEL, f"🎞️ **Album Upload Successfully** (Group ID: `{message.media_group_id}`)")
            except: pass

        except Exception as e:
            logging.error(e)
        finally:
            processed_albums.discard(message.media_group_id)
        return

    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        # 📤 File Upload Successfully Log
        try:
            file_name = file_info.get('name', 'Unknown')
            await client.send_message(LOG_CHANNEL, f"📤 **File Upload Successfully:** `{file_name}`")
        except: pass

# --- 5. ऑटो सर्च (Admin Access Only) ---
@app.on_message(filters.text & ~filters.command(["start", "broadcast", "stats"]))
async def auto_search(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.reply("❌ केवल एडमिन ही इस बॉट में सर्च कर सकते हैं।")

    query = message.text
    # 30 की लिमिट ताकि सारे बटन आ सकें
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=30)
    if not files: 
        return await message.reply("❌ कोई फाइल नहीं मिली। / No file found.")
    
    buttons = []
    processed_groups = set()
    
    for f in files:
        if f.get("media_group_id"):
            if f["media_group_id"] not in processed_groups:
                album_link = f"https://t.me/{BOT_USERNAME}?start=getalbum_{f['media_group_id']}"
                btn = [types.InlineKeyboardButton(f"📥 Album: {f['name']}", url=album_link)]
                buttons.append(btn)
                processed_groups.add(f["media_group_id"])
        else:
            unique_link = f"https://t.me/{BOT_USERNAME}?start=getfile_{f['_id']}"
            file_size = format_size(f.get("file_size", 0))
            btn = [types.InlineKeyboardButton(f"📥 File: {f['name']} ({file_size})", url=unique_link)]
            buttons.append(btn)

    await message.reply(f"📂 **'{query}' के लिए रिजल्ट्स:**", reply_markup=types.InlineKeyboardMarkup(buttons))

# --- स्टार्टअप सीक्वेंस ---
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    loop.run_until_complete(create_indexes())
    
    try:
        app.start()
        print("✅ Bot is online!")
        
        loop.create_task(keep_alive())
        loop.create_task(send_daily_report())
        idle()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        app.stop()
        
