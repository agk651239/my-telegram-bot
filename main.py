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

# --- फंक्शन: मैसेज ऑटो-डिलीट (3600 सेकंड = 1 घंटा - पॉइंट 8) ---
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

# --- 3. हेल्प कमांड (/help - पॉइंट 9: यह डिलीट नहीं होगा) ---
@app.on_message(filters.command("help"))
async def help_handler(client, message):
    help_text = (
        f"🛠️ **सहायता केंद्र / Help Menu**\n\n"
        f"• **फाइल कैसे खोजें?** बोट में कोई भी नाम लिखकर सर्च करें (केवल एडमिन के लिए)।\n"
        f"• **वेरिफिकेशन प्रक्रिया:** फाइल या एल्बम लिंक पर क्लिक करने के बाद एक बार **'Verify Now'** बटन पर क्लिक करके लिंक पूरा करें। यह वेरिफिकेशन अगले **{VERIFY_EXPIRE_HOURS}** घंटों के लिए वैध रहेगा。\n"
        f"• **ऑटो-डिलीट:** भेजी गई फाइलें सुरक्षा की दृष्टि से 1 घंटे बाद अपने आप डिलीट हो जाती हैं。\n\n"
        f"यदि आपको कोई समस्या आ रही है, तो कृपया ट्यूटोरियल लिंक की मदद लें।"
    )
    buttons = [
        [types.InlineKeyboardButton("💬 एडमिन से बात करें / Contact Admin", callback_data="ask_admin")]
    ]
    if TUTORIAL_URL:
        buttons.append([types.InlineKeyboardButton("❓ ट्यूटोरियल देखें / How to Verify", url=TUTORIAL_URL)])
    
    await message.reply_text(help_text, reply_markup=types.InlineKeyboardMarkup(buttons))

# --- 🆕 नए एडमिन कमांड्स और फीचर्स (पॉइंट 1, 2, 6, 7) ---

# प्राइस सेट करना (/setprice)
@app.on_message(filters.command("setprice") & filters.user(ADMIN_IDS))
async def setprice_cmd(client, message):
    prices = await get_plan_prices()
    text = "💰 **वर्तमान प्लान प्राइसेस / Current Plan Prices:**\n\n"
    for k, v in prices.items():
        text += f"• `{k}`: ₹{v}\n"
    text += "\nबदलाव के लिए भेजें: `/updateprice <plan_key> <price>`\nउदा: `/updateprice 30days 150`"
    await message.reply(text)

@app.on_message(filters.command("updateprice") & filters.user(ADMIN_IDS))
async def updateprice_cmd(client, message):
    args = message.text.split()
    if len(args) < 3:
        return await message.reply("❌ सही फॉर्मेट: `/updateprice 30days 150`")
    plan_key, price = args[1], int(args[2])
    await set_plan_price(plan_key, price)
    await message.reply(f"✅ प्लान `{plan_key}` का नया प्राइस ₹{price} सेट हो गया है!")

# नो-बायपास सेट करना (/nobypass <user_id>)
@app.on_message(filters.command("nobypass") & filters.user(ADMIN_IDS))
async def nobypass_cmd(client, message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("❌ सही फॉर्मेट: `/nobypass <user_id>`")
    try:
        target_user = int(args[1])
    except ValueError:
        return await message.reply("❌ यूजर आईडी सही संख्या होनी चाहिए।")
    
    buttons = [
        [types.InlineKeyboardButton("7 दिन / Days", callback_data=f"nb_{target_user}_7"),
         types.InlineKeyboardButton("30 दिन / Days", callback_data=f"nb_{target_user}_30")],
        [types.InlineKeyboardButton("3 महीने / Months", callback_data=f"nb_{target_user}_90"),
         types.InlineKeyboardButton("लाइफटाइम / Lifetime", callback_data=f"nb_{target_user}_life")]
    ]
    await message.reply(f"⏳ यूजर `{target_user}` के लिए प्रीमियम अवधि चुनें:", reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^nb_"))
async def nobypass_callback(client, callback_query):
    if callback_query.from_user.id not in ADMIN_IDS:
        return await callback_query.answer("❌ आप एडमिन नहीं हैं!", show_alert=True)
    
    _, target_user, duration_type = callback_query.data.split("_")
    target_user = int(target_user)
    
    if duration_type == "life":
        seconds = -1
        text_msg = "Lifetime (अनंत काल)"
    else:
        days = int(duration_type)
        seconds = days * 86400
        text_msg = f"{days} दिन (Days)"
        
    await set_user_premium_duration(target_user, seconds)
    await callback_query.message.edit_text(f"✅ यूजर `{target_user}` को सफलताપूर्व {text_msg} के लिए प्रीमियम/बायपास दे दिया गया है!")
    try:
        await client.send_message(target_user, f"🎉 **बधाई हो!** एडमिन द्वारा आपको {text_msg} के लिए प्रीमियम एक्सेस दे दिया गया है। अब आप बिना किसी रुकावट के फाइलें डाउनलोड कर सकते हैं।")
    except:
        pass

# QR कोड अपडेट करना (/set_qr)
@app.on_message(filters.command("set_qr") & filters.user(ADMIN_IDS))
async def set_qr_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply("❌ कृपया नए QR कोड की फोटो पर रिप्लाई करके `/set_qr` लिखें।")
    photo_id = message.reply_to_message.photo.file_id
    await save_qr_code(photo_id)
    await message.reply("✅ नया पेमेंट QR कोड सफलताપूर्व अपडेट हो गया है!")

# लाइव चैट सिस्टम (/connect और /problemsolve)
@app.on_message(filters.command("connect") & filters.user(ADMIN_IDS))
async def connect_cmd(client, message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("❌ सही फॉर्मेट: `/connect <user_id>`")
    try:
        u_id = int(args[1])
    except:
        return await message.reply("❌ अमान्य यूजर आईडी।")
    
    await db.settings.update_one({"type": "live_chat"}, {"$set": {"active_admin": message.from_user.id, "active_user": u_id}}, upsert=True)
    await message.reply(f"🟢 यूजर `{u_id}` के साथ लाइव चैट शुरू हो गई है। अब आप जो भी मैसेज भेजेंगे वह यूजर को जाएगा।")
    try:
        await client.send_message(u_id, "💬 **एडमिन आपके साथ लाइव चैट पर जुड़ गए हैं। आप अपनी समस्या यहाँ बता सकते हैं।**")
    except:
        pass

@app.on_message(filters.command("problemsolve") & filters.user(ADMIN_IDS))
async def problemsolve_cmd(client, message):
    res = await db.settings.find_one({"type": "live_chat"})
    if res and res.get("active_user"):
        u_id = res["active_user"]
        await db.settings.delete_one({"type": "live_chat"})
        await message.reply(f"🔴 यूजर `{u_id}` के साथ लाइव चैट सत्र बंद कर दिया गया है।")
        try:
            await client.send_message(u_id, "🔒 **एडमिन ने आपकी समस्या का समाधान कर दिया है और चैट सत्र समाप्त कर दिया है।**")
        except:
            pass
    else:
        await message.reply("❌ कोई भी सक्रिय लाइव चैट सत्र नहीं है।")

@app.on_callback_query(filters.regex("ask_admin"))
async def ask_admin_cb(client, callback_query):
    u_id = callback_query.from_user.id
    await db.settings.update_one({"type": "live_chat"}, {"$set": {"active_user": u_id}}, upsert=True)
    await callback_query.message.reply("✅ आपका अनुरोध एडमिन तक पहुँचा दिया गया है। कृपया अपनी समस्या यहाँ लिखकर भेजें, एडमिन जल्द ही आपसे जुड़ेंगे।")
    await callback_query.answer()
    if ADMIN_ID:
        try:
            await client.send_message(ADMIN_ID, f"⚠️ **नया सहायता अनुरोध (Help Request):**\nयूजर: {callback_query.from_user.mention} (`{u_id}`)\nलाइव चैट से जुड़ने के लिए भेजें: `/connect {u_id}`")
        except:
            pass

# --- नए यूजर और एडमिन कमांड्स (/myplan, /pricing, /users, /addadmin, /removeadmin) ---
@app.on_message(filters.command("myplan"))
async def my_plan_handler(client, message):
    user_id = message.from_user.id
    user_data = await db.users.find_one({"user_id": user_id})
    if not user_data:
        return await message.reply("❌ आपका डेटा नहीं मिला। कृपया पहले `/start` भेजें।")
    expire_at = user_data.get("expire_at", 0)
    current_time = time.time()
    if user_id in ADMIN_IDS:
        status_text = "👑 **आप एडमिन हैं (Admin Access)**\n• आपके पास असीमित और आजीवन एक्सेस है।"
    elif expire_at == float('inf'):
        status_text = "💎 **प्रीमियम स्टेटस: सक्रिय (Lifetime)**\n• आपका प्रीमियम लाइफटाइम के लिए वैध है।"
    elif expire_at > current_time:
        rem = int(expire_at - current_time)
        hrs = rem // 3600
        days = hrs // 24
        time_left = f"लगभग {days} दिन बाकी हैं" if days > 0 else f"लगभग {hrs} घंटे बाकी हैं"
        status_text = f"✅ **प्रीमियम/वेरिफिकेशन सक्रिय है**\n• वैध अवधि समाप्त होने में: `{time_left}`"
    else:
        status_text = "❌ **कोई सक्रिय प्लान नहीं है (Expired)**\n• फाइल डाउनलोड करने के लिए वेरीफाई करें या प्रीमियम खरीदें।"
    buttons = [[types.InlineKeyboardButton("💎 प्रीमियम प्लान देखें / View Plans", callback_data="buy_premium_menu")]]
    await message.reply(status_text, reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_message(filters.command(["pricing", "plans"]))
async def pricing_handler(client, message):
    prices = await get_plan_prices()
    text = (
        f"💎 **उपलब्ध प्रीमियम प्लान्स और मूल्य / Available Plans & Prices:**\n\n"
        f"• **7 दिन:** ₹{prices.get('7days', 0)}\n"
        f"• **15 दिन:** ₹{prices.get('15days', 0)}\n"
        f"• **30 दिन:** ₹{prices.get('30days', 0)}\n"
        f"• **3 महीने:** ₹{prices.get('3months', 0)}\n"
        f"• **6 महीने:** ₹{prices.get('6months', 0)}\n"
        f"• **1 वर्ष:** ₹{prices.get('1year', 0)}\n"
        f"• **लाइफटाइम:** ₹{prices.get('lifetime', 0)}\n\n"
        f"खरीदने के लिए नीचे दिए गए बटन पर क्लिक करें:"
    )
    buttons = [[types.InlineKeyboardButton("💳 अभी खरीदें / Buy Now", callback_data="buy_premium_menu")]]
    await message.reply(text, reply_markup=types.InlineKeyboardMarkup(buttons))

@app.on_message(filters.command("users") & filters.user(ADMIN_IDS))
async def total_users_handler(client, message):
    total_users = await db.users.count_documents({})
    verified_count = await db.users.count_documents({"expire_at": {"$gt": time.time()}})
    text = (
        f"📊 **यूजर सांख्यिकी / User Statistics:**\n\n"
        f"👥 **कुल रजिस्टर्ड यूजर्स:** `{total_users}`\n"
        f"✅ **सक्रिय प्रीमियम/वेरिफाइड यूजर्स:** `{verified_count}`"
    )
    await message.reply(text)

@app.on_message(filters.command("addadmin") & filters.user(ADMIN_ID))
async def add_admin_handler(client, message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("❌ सही फॉर्मेट: `/addadmin <user_id>`")
    try:
        new_adm = int(args[1])
    except ValueError:
        return await message.reply("❌ यूजर आईडी केवल अंक होनी चाहिए।")
    if new_adm in ADMIN_IDS:
        return await message.reply("⚠️ यह यूजर पहले से ही एडमिन सूची में है।")
    await db.settings.update_one({"type": "extra_admins"}, {"$addToSet": {"admins": new_adm}}, upsert=True)
    if new_adm not in ADMIN_IDS:
        ADMIN_IDS.append(new_adm)
    await message.reply(f"✅ यूजर `{new_adm}` को सफलताપूर्व एडमिन बना दिया गया है!")

@app.on_message(filters.command("removeadmin") & filters.user(ADMIN_ID))
async def remove_admin_handler(client, message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("❌ सही फॉर्मेट: `/removeadmin <user_id>`")
    try:
        old_adm = int(args[1])
    except ValueError:
        return await message.reply("❌ यूजर आईडी केवल अंक होनी चाहिए।")
    if old_adm == ADMIN_ID:
        return await message.reply("❌ मुख्य एडमिन को हटाया नहीं जा सकता!")
    await db.settings.update_one({"type": "extra_admins"}, {"$pull": {"admins": old_adm}})
    if old_adm in ADMIN_IDS:
        ADMIN_IDS.remove(old_adm)
    await message.reply(f"✅ यूजर `{old_adm}` को एडमिन सूची से हटा दिया गया है।")

# --- 4. स्टार्ट कमांड (फोर्स चैनल चेकिंग + वेरिफिकेशन टाइम + प्रीमियम बटन - पॉइंट 3, 4) ---
@app.on_message(filters.command("start"))
async def start(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    is_admin = (user_id in ADMIN_IDS)
    
    # लाइव चैट मैसेज फॉरवर्डिंग (यदि यूजर चैट मोड में है)
    live_data = await db.settings.find_one({"type": "live_chat"})
    if live_data and not is_admin:
        if live_data.get("active_user") == user_id:
            adm = live_data.get("active_admin")
            if adm:
                try:
                    await message.forward(adm)
                    return
                except:
                    pass

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
            f"अब आप अगले {VERIFY_EXPIRE_HOURS} घंटों के लिए असीमित फाइलें और एल्बम डाउनलोड कर सकते हैं。\n"
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
                    ch_id = int(channel) if str(channel).startswith("-") or str(channel).isdigit() else channel
                    member = await client.get_chat_member(ch_id, user_id)
                    if member.status in ["left", "kicked"]:
                        raise Exception("Not joined")
                except Exception:
                    try:
                        ch_id = int(channel) if str(channel).startswith("-") or str(channel).isdigit() else channel
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
                [types.InlineKeyboardButton("💎 प्रीमियम खरीदें / Buy Premium", callback_data="buy_premium_menu")],
                [types.InlineKeyboardButton("❓ वेरिफ़ाई कैसे करें? / How to Verify?", url=TUTORIAL_URL)]
            ]
            await message.reply(
                f"🔐 **वेरिफ़िकेशन आवश्यक है / Verification Required**\n\n"
                f"Verify once to get unlimited access for the next {VERIFY_EXPIRE_HOURS} hours.\n"
                f"अगले {VERIFY_EXPIRE_HOURS} घंटों के लिए असीमित फाइल डाउनलोड करने हेतु एक बार वेरिफ़ाई करें या प्रीमियम लें।",
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
                [types.InlineKeyboardButton("💎 प्रीमियम खरीदें / Buy Premium", callback_data="buy_premium_menu")],
                [types.InlineKeyboardButton("❓ वेरिफ़ाई कैसे करें? / How to Verify?", url=TUTORIAL_URL)]
            ]
            await message.reply(
                f"🔐 **वेरिफ़िकेशन आवश्यक है / Verification Required**\n\n"
                f"Verify once to get unlimited access for the next {VERIFY_EXPIRE_HOURS} hours.\n"
                f"अगले {VERIFY_EXPIRE_HOURS} घंटों के लिए असीमित एल्बम डाउनलोड करने हेतु एक बार वेरिफ़ाई करें या प्रीमियम लें।",
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

# --- 💡 प्रीमियम खरीद प्रक्रिया (Buy Premium Flow - बिना फिक्स प्राइस के) ---
@app.on_callback_query(filters.regex("buy_premium_menu"))
async def buy_premium_menu_cb(client, callback_query):
    prices = await get_plan_prices()
    buttons = [
        [types.InlineKeyboardButton(f"7 दिन (Days) - ₹{prices.get('7days', 0)}", callback_data="buyplan_7days"),
         types.InlineKeyboardButton(f"15 दिन (Days) - ₹{prices.get('15days', 0)}", callback_data="buyplan_15days")],
        [types.InlineKeyboardButton(f"30 दिन (Days) - ₹{prices.get('30days', 0)}", callback_data="buyplan_30days"),
         types.InlineKeyboardButton(f"3 महीने (Months) - ₹{prices.get('3months', 0)}", callback_data="buyplan_3months")],
        [types.InlineKeyboardButton(f"6 महीने (Months) - ₹{prices.get('6months', 0)}", callback_data="buyplan_6months"),
         types.InlineKeyboardButton(f"1 वर्ष (Year) - ₹{prices.get('1year', 0)}", callback_data="buyplan_1year")],
        [types.InlineKeyboardButton(f"लाइफटाइम (Lifetime) - ₹{prices.get('lifetime', 0)}", callback_data="buyplan_lifetime")]
    ]
    await callback_query.message.edit_text("💎 **अपना प्रीमियम प्लान चुनें / Select Your Premium Plan:**", reply_markup=types.InlineKeyboardMarkup(buttons))
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^buyplan_"))
async def plan_selected_cb(client, callback_query):
    plan_key = callback_query.data.split("buyplan_")[1]
    prices = await get_plan_prices()
    amount = prices.get(plan_key, 0)
    
    qr_id = await get_qr_code()
    pay_text = (
        f"💳 **प्रीमियम पेमेंट विवरण / Payment Details**\n\n"
        f"• **चयनित प्लान / Selected Plan:** `{plan_key}`\n"
        f"• **राशि / Amount:** `₹{amount}`\n"
        f"• **UPI ID:** `{UPI_ID}`\n\n"
        f"कृपया ऊपर दिए गए UPI ID या QR Code पर भुगतान करें, और भुगतान करने के बाद नीचे दिए गए बटन पर क्लिक करके **पेमेंट का स्क्रीनशॉट (फोटो)** भेजें।"
    )
    buttons = [[types.InlineKeyboardButton("✅ मैंने पेमेंट कर दिया है (I have Paid)", callback_data=f"paid_{plan_key}")]]
    
    if qr_id:
        try:
            await client.send_photo(callback_query.message.chat.id, qr_id, caption=pay_text, reply_markup=types.InlineKeyboardMarkup(buttons))
            await callback_query.message.delete()
            return
        except:
            pass
    
    await callback_query.message.edit_text(pay_text, reply_markup=types.InlineKeyboardMarkup(buttons))
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^paid_"))
async def user_paid_cb(client, callback_query):
    plan_key = callback_query.data.split("paid_")[1]
    
    # तुरंत डेटाबेस में सही प्लान अपडेट करें (फिक्स किया गया)
    await db.users.update_one(
        {"user_id": callback_query.from_user.id}, 
        {"$set": {"pending_plan": plan_key}},
        upsert=True
    )
    
    await callback_query.message.edit_text(
        f"📤 **चयनित प्लान / Selected Plan:** `{plan_key}`\n\n"
        f"**अब अपने पेमेंट का स्क्रीनशॉट (फोटो) इस चैट में भेजें।**\n\n"
        f"Send your payment screenshot photo now."
    )
    await callback_query.answer()

@app.on_message(filters.photo)
async def payment_screenshot_handler(client, message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        return
    
    user_data = await db.users.find_one({"user_id": user_id})
    pending_plan = user_data.get("pending_plan", "30days") if user_data else "30days"
    
    if ADMIN_ID:
        try:
            caption = (
                f"💳 **नया पेमेंट स्क्रीनशॉट प्राप्त हुआ!**\n\n"
                f"👤 यूजर: {message.from_user.mention} (`{user_id}`)\n"
                f"📦 प्लान: `{pending_plan}`\n\n"
                f"इसे एक्टिव करने के लिए नीचे क्लिक करें:"
            )
            days_map = {"7days": 7, "15days": 15, "30days": 30, "3months": 90, "6months": 180, "1year": 365, "lifetime": -1}
            d_val = days_map.get(pending_plan, 30)
            
            buttons = [[types.InlineKeyboardButton("⚡ प्रीमियम एक्टिव करें (/nobypass)", callback_data=f"nb_{user_id}_{d_val if d_val != -1 else 'life'}")]]
            await message.forward(ADMIN_ID)
            await client.send_message(ADMIN_ID, caption, reply_markup=types.InlineKeyboardMarkup(buttons))
            await message.reply("✅ **आपका पेमेंट स्क्रीनशॉट एडमिन के पास भेज दिया गया है।**\nजाँच के बाद आपका प्रीमियम एक्टिव कर दिया जाएगा।")
        except Exception as e:
            await message.reply(f"❌ एरर: {e}")

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

# --- 6. ऑटो सर्च और लाइव चैट मैसेज फॉरवर्डिंग ---
@app.on_message(filters.text & ~filters.command(["start", "broadcast", "stats", "help", "setprice", "updateprice", "nobypass", "set_qr", "connect", "problemsolve", "myplan", "pricing", "plans", "users", "addadmin", "removeadmin"]))
async def auto_search(client, message):
    user_id = message.from_user.id
    
    # 1. यदि एडमिन लाइव चैट मोड में है तो मैसेज सीधे यूजर को जाए
    if user_id in ADMIN_IDS:
        live_data = await db.settings.find_one({"type": "live_chat"})
        if live_data and live_data.get("active_admin") == user_id:
            u_id = live_data.get("active_user")
            if u_id:
                try:
                    await message.copy(u_id)
                    return
                except Exception as e:
                    await message.reply(f"❌ यूजर को भेजने में एरर: {e}")
                    return

    # 2. यदि यूजर लाइव चैट मोड में है तो मैसेज सीधे एडमिन को जाए
    live_data = await db.settings.find_one({"type": "live_chat"})
    if live_data and live_data.get("active_user") == user_id:
        adm = live_data.get("active_admin")
        if adm:
            try:
                await message.forward(adm)
                return
            except:
                pass

    if user_id not in ADMIN_IDS:
        return

    query = message.text
    files = await db.files.find({"name": {"$regex": query, "$options": "i"}}).to_list(length=30000)
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
        
