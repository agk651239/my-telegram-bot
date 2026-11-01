from pyrogram import Client, filters, types
from pyrogram.errors import UserIsBlocked, InputUserDeactivated
import asyncio
import logging
import time
from config import *
from database import * 

# --- 1. ब्रॉडकास्ट कमांड ---
@Client.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
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
@Client.on_message(filters.command("stats") & filters.user(ADMIN_IDS))
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

# प्राइस सेट करना (/setprice)
@Client.on_message(filters.command("setprice") & filters.user(ADMIN_IDS))
async def setprice_cmd(client, message):
    prices = await get_plan_prices()
    text = "💰 **वर्तमान प्लान प्राइसेस / Current Plan Prices:**\n\n"
    for k, v in prices.items():
        text += f"• `{k}`: ₹{v}\n"
    text += "\nबदलाव के लिए भेजें: `/updateprice <plan_key> <price>`\nउदा: `/updateprice 30days 150`"
    await message.reply(text)

@Client.on_message(filters.command("updateprice") & filters.user(ADMIN_IDS))
async def updateprice_cmd(client, message):
    args = message.text.split()
    if len(args) < 3:
        return await message.reply("❌ सही फॉर्मेट: `/updateprice 30days 150`")
    plan_key, price = args[1], int(args[2])
    await set_plan_price(plan_key, price)
    await message.reply(f"✅ प्लान `{plan_key}` का नया प्राइस ₹{price} सेट हो गया है!")

# नो-बायपास सेट करना (/nobypass <user_id>)
@Client.on_message(filters.command("nobypass") & filters.user(ADMIN_IDS))
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

@Client.on_callback_query(filters.regex(r"^nb_"))
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
    await callback_query.message.edit_text(f"✅ यूजर `{target_user}` को सफलतापूर्वक {text_msg} के लिए प्रीमियम/बायपास दे दिया गया है!")
    try:
        await client.send_message(target_user, f"🎉 **बधाई हो!** एडमिन द्वारा आपको {text_msg} के लिए प्रीमियम एक्सेस दे दिया गया है। अब आप बिना किसी रुकावट के फाइलें डाउनलोड कर सकते हैं।")
    except:
        pass

# QR कोड अपडेट करना (/set_qr)
@Client.on_message(filters.command("set_qr") & filters.user(ADMIN_IDS))
async def set_qr_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply("❌ कृपया नए QR कोड की फोटो पर रिप्लाई करके `/set_qr` लिखें।")
    photo_id = message.reply_to_message.photo.file_id
    await save_qr_code(photo_id)
    await message.reply("✅ नया पेमेंट QR कोड सफलतापूर्वक अपडेट हो गया है!")

# लाइव चैट सिस्टम (/connect और /problemsolve)
@Client.on_message(filters.command("connect") & filters.user(ADMIN_IDS))
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

@Client.on_message(filters.command("problemsolve") & filters.user(ADMIN_IDS))
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

@Client.on_message(filters.command("users") & filters.user(ADMIN_IDS))
async def total_users_handler(client, message):
    total_users = await db.users.count_documents({})
    verified_count = await db.users.count_documents({"expire_at": {"$gt": time.time()}})
    text = (
        f"📊 **यूजर सांख्यिकी / User Statistics:**\n\n"
        f"👥 **कुल रजिस्टर्ड यूजर्स:** `{total_users}`\n"
        f"✅ **सक्रिय प्रीमियम/वेरिफाइड यूजर्स:** `{verified_count}`"
    )
    await message.reply(text)

@Client.on_message(filters.command("addadmin") & filters.user(ADMIN_ID))
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
    await message.reply(f"✅ यूजर `{new_adm}` को सफलतापूर्वक एडमिन बना दिया गया है!")

@Client.on_message(filters.command("removeadmin") & filters.user(ADMIN_ID))
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
