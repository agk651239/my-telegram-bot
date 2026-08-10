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

# --- प्रीमियम स्टेबिलिटी (वेब-सर्वर SSL सपोर्ट के साथ पोर्ट 10000) ---
async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', lambda r: web.Response(text="Bot is running successfully!"))
    
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
        await asyncio.sleep(86400)
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

# --- गुमशुदा वेरिएबल्स (Missing Keys) की चेतावनी भेजने का फंक्शन ---
async def send_missing_keys_alert():
    if missing_keys and ADMIN_ID:
        try:
            keys_str = ", ".join(missing_keys)
            alert_text = (
                f"⚠️ **कॉन्फ़िगरेशन चेतावनी / Missing Keys Alert**\n\n"
                f"रेंडर में निम्नलिखित पर्यावरण चर (Environment Variables) गायब या अनकॉफ़िगर हैं:\n"
                f"`{keys_str}`"
            )
            await app.send_message(ADMIN_ID, alert_text)
        except Exception:
            pass

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
            try:
                await client.send_message(LOG_CHANNEL, f"🚫 **User Blocked Bot:** `{user['user_id']}`")
            except Exception as e:
                logging.error(f"Log Error (User Blocked): {e}")
        except: 
            pass
    await message.reply(f"✅ मैसेज {success} यूजर्स को भेज दिया गया। (ब्लॉक किए गए: {blocked})")

# --- 2. स्टेटस कमांड (Advanced /stats) ---
@app.on_message(filters.command("stats") & filters.user(ADMIN_IDS))
async def stats_handler(client, message):
    total_users = await db.users.count_documents({})
    total_files = await db.files.count_documents({})
    verified_users = await db.users.count_documents({"expire_at": {"$gt": time.time()}})
    
    bot_info = await client.get_me()
    bot_name = bot_info.first_name
    bot_username = f"@{bot_info.username}" if bot_info.username else "No Username"
    
    stats_text = (
        f"📊 **बोट सांख्यिकी रिपोर्ट / Bot Statistics Report**\n\n"
        f"🤖 **बोट का नाम / Bot Name:** `{bot_name}`\n"
        f"🔗 **बोट यूज़रनेम / Bot Username:** `{bot_username}`\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"✅ **Verified Users:** `{verified_users}`\n"
        f"📂 **Total Indexed Files:** `{total_files}`\n"
        f"🟢 **Status:** सभी प्रणालियाँ कार्यरत हैं / All Systems Operational"
    )
    await message.reply(stats_text)
    try:
        await client.send_message(LOG_CHANNEL, f"📊 **Advanced /stats checked by Admin:** `{message.from_user.id}`")
    except Exception as e:
        logging.error(f"Log Error (/stats): {e}")

# --- 3. हेल्प कमांड (/help) ---
@app.on_message(filters.command("help"))
async def help_handler(client, message):
    help_text = (
        f"🛠️ **सहायता केंद्र / Help Menu**\n\n"
        f"• **फाइल कैसे खोजें?** बोट में कोई भी नाम लिखकर सर्च करें (केवल एडमिन के लिए)।\n"
        f"• **वेरिफिकेशन प्रक्रिया:** फाइल या एल्बम लिंक पर क्लिक करने के बाद एक बार **'Verify Now'** बटन पर क्लिक करके लिंक पूरा करें। यह वेरिफिकेशन अगले **{VERIFY_EXPIRE_HOURS}** घंटों के लिए वैध रहेगा।\n"
        f"• **ऑटो-डिलीट:** भेजी गई फाइलें सुरक्षा की दृष्टि से 1 घंटे बाद अपने आप डिलीट हो जाती हैं।\n\n"
        f"यदि आपको कोई समस्या आ रही है, तो कृपया ट्यूटोरियल लिंक की मदद लें।"
    )
    buttons = []
    if TUTORIAL_URL:
        buttons.append([types.InlineKeyboardButton("❓ ट्यूटोरियल देखें / How to Verify", url=TUTORIAL_URL)])
    
    await message.reply_text(help_text, reply_markup=types.InlineKeyboardMarkup(buttons) if buttons else None)

# --- 4. स्टार्ट कमांड (फोर्स चैनल चेकिंग + वेरिफिकेशन टाइम मैसेज के साथ) ---
@app.on_message(filters.command("start"))
async def start(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    is_admin = (user_id in ADMIN_IDS)
    
    if not await db.users.find_one({"user_id": user_id}):
        await add_user(user_id)
        total_users = await db.users.count_documents({})
        try: 
            await client.send_message(
                LOG_CHANNEL, 
                f"🆕 **New User Joined:** `{user_id}`\n📊 **Total Users:** `{total_users}`"
            )
        except Exception as e:
            logging.error(f"Log Error (New User): {e}")
    
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
        
        try:
            await client.send_message(LOG_CHANNEL, f"✅ **Verification Completed:** `{user_id}`")
        except Exception as e:
            logging.error(f"Log Error (Verification Completed): {e}")

        await message.reply(
            f"✅ **वेरिफ़िकेशन सफल रहा! / Verification Successful!**\n\n"
            f"अब आप अगले {VERIFY_EXPIRE_HOURS} घंटों के लिए असीमित फाइलें और एल्बम डाउनलोड कर सकते हैं।\n"
            "Now you can download files seamlessly. Send your link again!"
        )
        return

    # --- Force Channels Check (Public & Private) ---
    if not is_admin:
        if PUBLIC_CHANNELS:
            for channel in PUBLIC_CHANNELS:
                try:
                    member = await client.get_chat_member(channel, user_id)
                    if member.status in ["left", "kicked"]:
                        raise Exception("Not joined")
                except Exception:
                    clean_channel = channel.replace("@", "").strip()
                    channel_link = f"https://t.me/{clean_channel}"
                    join_buttons = [
                        [types.InlineKeyboardButton("📢 पब्लिक चैनल ज्वाइन करें / Join Public Channel", url=channel_link)],
                        [types.InlineKeyboardButton("🔄 दोबारा जाँच करें / Try Again", url=f"https://t.me/{BOT_USERNAME}?start=start")]
                    ]
                    return await message.reply_text(
                        "⚠️ **चैनल ज्वाइन करना अनिवार्य है! / Force Join Required!**\n\n"
                        "बोट का उपयोग करने के लिए कृपया हमारे पब्लिक चैनल को ज्वाइन करें।",
                        reply_markup=types.InlineKeyboardMarkup(join_buttons)
                    )

        if PRIVATE_CHANNELS:
            for channel in PRIVATE_CHANNELS:
                channel_link = "https://t.me"
                if "t.me/" in str(channel) or "+" in str(channel):
                    channel_link = channel if channel.startswith("http") else f"https://t.me/{channel}"
                    join_buttons = [
                        [types.InlineKeyboardButton("🔒 प्राइवेट चैनल ज्वाइन करें / Join Private Channel", url=channel_link)],
                        [types.InlineKeyboardButton("🔄 दोबारा जाँच करें / Try Again", url=f"https://t.me/{BOT_USERNAME}?start=start")]
                    ]
                    return await message.reply_text(
                        "⚠️ **चैनल ज्वाइन करना अनिवार्य है! / Force Join Required!**\n\n"
                        "बोट का उपयोग करने के लिए कृपया हमारे प्राइवेट चैनल को ज्वाइन करें।",
                        reply_markup=types.InlineKeyboardMarkup(join_buttons)
                    )

                try:
                    ch_id = int(channel) if channel.startswith("-") or channel.isdigit() else channel
                    member = await client.get_chat_member(ch_id, user_id)
                    if member.status in ["left", "kicked"]:
                        raise Exception("Not joined")
                except Exception:
                    try:
                        ch_id = int(channel) if channel.startswith("-") or channel.isdigit() else channel
                        chat = await client.get_chat(ch_id)
                        channel_link = chat.invite_link or (f"https://t.me/{chat.username}" if chat.username else "https://t.me")
                    except Exception:
                        channel_link = "https://t.me"

                    join_buttons = [
                        [types.InlineKeyboardButton("🔒 प्राइवेट चैनल ज्वाइन करें / Join Private Channel", url=channel_link)],
                        [types.InlineKeyboardButton("🔄 दोबारा जाँच करें / Try Again", url=f"https://t.me/{BOT_USERNAME}?start=start")]
                    ]
                    return await message.reply_text(
                        "⚠️ **चैनल ज्वाइन करना अनिवार्य है! / Force Join Required!**\n\n"
                        "बोट का उपयोग करने के लिए कृपया हमारे प्राइवेट चैनल को ज्वाइन करें।",
                        reply_markup=types.InlineKeyboardMarkup(join_buttons)
                    )

        if FORCE_SUB_ENABLED and FORCE_SUB_CHANNEL:
            try: 
                await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
            except Exception as e:
                logging.info(f"Force sub check failed for user {user_id}: {e}")
                btn = [[types.InlineKeyboardButton("🔗 चैनल जॉइन करें / Join Channel", url=FORCE_SUB_LINK)]]
                return await message.reply("⚠️ **पहले चैनल जॉइन करें! / Please join the channel first!**", reply_markup=types.InlineKeyboardMarkup(btn))

    if len(command) > 1 and "getfile_" in command[1]:
        file_id = command[1].split("getfile_")[1]

        if user_id not in ADMIN_IDS and not await is_verified(user_id):
            unique_token = secrets.token_hex(6)
            await db.users.update_one(
                {"user_id": user_id}, 
                {"$set": {"verify_token": unique_token, "token_used": False}}
            )
            
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}_{unique_token}")
            
            try:
                await client.send_message(LOG_CHANNEL, f"⚠️ **Verification Pending:** `{user_id}` requested file.")
            except Exception as e:
                logging.error(f"Log Error (Verification Pending File): {e}")

            buttons = [
                [types.InlineKeyboardButton("🔗 अभी वेरिफ़ाई करें / Verify Now", url=short_link)],
                [types.InlineKeyboardButton("❓ वेरिफ़ाई कैसे करें? / How to Verify?", url=TUTORIAL_URL)]
            ]
            await message.reply(
                f"🔐 **वेरिफ़िकेशन आवश्यक है / Verification Required**\n\n"
                f"Verify once to get unlimited access for the next {VERIFY_EXPIRE_HOURS} hours.\n"
                f"अगले {VERIFY_EXPIRE_HOURS} घंटों के लिए असीमित फाइल डाउनलोड करने हेतु एक बार वेरिफ़ाई करें।",
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
        if user_id not in ADMIN_IDS and not await is_verified(user_id):
            unique_token = secrets.token_hex(6)
            await db.users.update_one(
                {"user_id": user_id}, 
                {"$set": {"verify_token": unique_token, "token_used": False}}
            )
            
            short_link = await get_shortlink(f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}_{unique_token}")
            
            try:
                await client.send_message(LOG_CHANNEL, f"⚠️ **Verification Pending:** `{user_id}` requested album.")
            except Exception as e:
                logging.error(f"Log Error (Verification Pending Album): {e}")

            buttons = [
                [types.InlineKeyboardButton("🔗 अभी वेरिफ़ाई करें / Verify Now", url=short_link)],
                [types.InlineKeyboardButton("❓ वेरिफ़ाई कैसे करें? / How to Verify?", url=TUTORIAL_URL)]
            ]
            await message.reply(
                f"🔐 **वेरिफ़िकेशन आवश्यक है / Verification Required**\n\n"
                f"Verify once to get unlimited access for the next {VERIFY_EXPIRE_HOURS} hours.\n"
                f"अगले {VERIFY_EXPIRE_HOURS} घंटों के लिए असीमित एल्बम डाउनलोड करने हेतु एक बार वेरिफ़ाई करें।",
                reply_markup=types.InlineKeyboardMarkup(buttons)
            )
            return

        try:
            group_id = int(command[1].split("getalbum_")[1])
        except ValueError:
            return await message.reply("❌ अमान्य एल्बम लिंक।")

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

        try:
            sent_msgs = await client.send_media_group(
                chat_id=message.chat.id,
                media=media_group
            )
            warn_msg = await message.reply(
                "⚠️ **आपकी फाइल 1 घंटे में अपने आप डिलीट हो जाएगी। कृपया इसे अभी सेव कर लें!**\n\n"
                "**Your file will be deleted automatically in 1 hour. Please save it now!**"
            )
            asyncio.create_task(delete_album_after_delay(sent_msgs, warn_msg, 3600))
        except Exception as e:
            await message.reply(f"❌ एल्बम भेजने में एरर: {e}")
        return
        
    await message.reply(START_MESSAGE)

# --- 5. फाइल इंडेक्सिंग ---
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
            
            try:
                await client.send_message(LOG_CHANNEL, f"🎞️ **Album Upload Successfully** (Group ID: `{message.media_group_id}`)")
            except Exception as e:
                logging.error(f"Log Error (Album Upload): {e}")

        except Exception as e:
            logging.error(e)
        finally:
            processed_albums.discard(message.media_group_id)
        return

    file_info = await get_file_info(message)
    if file_info:
        await add_file(file_info)
        try:
            file_name = file_info.get('name', 'Unknown')
            await client.send_message(LOG_CHANNEL, f"📤 **File Upload Successfully:** `{file_name}`")
        except Exception as e:
            logging.error(f"Log Error (File Upload): {e}")

# --- 6. ऑटो सर्च (Admin Access Only) ---
@app.on_message(filters.text & ~filters.command(["start", "broadcast", "stats", "help"]))
async def auto_search(client, message):
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        return

    query = message.text
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
        
        # मिसिंग कीज़ अलर्ट चेक करें
        loop.run_until_complete(send_missing_keys_alert())
        
        try:
            resolved_log_channel = LOG_CHANNEL
            if isinstance(LOG_CHANNEL, str):
                if "t.me/" in LOG_CHANNEL:
                    resolved_log_channel = "@" + LOG_CHANNEL.strip("/").split("t.me/")[-1]
                elif not LOG_CHANNEL.startswith("@") and not LOG_CHANNEL.startswith("-") and not LOG_CHANNEL.isdigit():
                    resolved_log_channel = "@" + LOG_CHANNEL
                elif LOG_CHANNEL.lstrip('-').isdigit():
                    resolved_log_channel = int(LOG_CHANNEL)
            
            loop.run_until_complete(app.send_message(resolved_log_channel, "🟢 **Bot Restarted & Log Channel Connected Successfully!**"))
        except Exception as e:
            print(f"⚠️ Log Channel Startup Warning: {e}")

        loop.create_task(keep_alive())
        loop.create_task(send_daily_report())
        idle()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        app.stop()
        
