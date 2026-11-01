from pyrogram import Client, filters, types
import secrets
import asyncio
import logging
import time
from config import *
from database import * 
from helpers import *

# --- फंक्शन: मैसेज ऑटो-डिलीट ---
async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

# --- फंक्शन: एल्बम ऑटो-डिलीट ---
async def delete_album_after_delay(client, messages, warn_msg, delay):
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await client.delete_messages(msg.chat.id, msg.id)
        except Exception:
            pass
    try:
        await warn_msg.delete()
    except Exception:
        pass

# हेल्प कमांड
@Client.on_message(filters.command("help"))
async def help_handler(client, message):
    help_text = (
        f"🛠️ **सहायता केंद्र / Help Menu**\n\n"
        f"• **फाइल कैसे खोजें?** बोट में कोई भी नाम लिखकर सर्च करें (केवल एडमिन के लिए)।\n"
        f"• **वेरिफिकेशन प्रक्रिया:** फाइल या एल्बम लिंक पर क्लिक करने के बाद एक बार **'Verify Now'** बटन पर क्लिक करके लिंक पूरा करें। यह वेरिफिकेशन अगले **{VERIFY_EXPIRE_HOURS}** घंटों के लिए वैध रहेगा।\n"
        f"• **ऑटो-डिलीट:** भेजी गई फाइलें सुरक्षा की दृष्टि से 1 घंटे बाद अपने आप डिलीट हो जाती हैं।\n\n"
        f"यदि आपको कोई समस्या आ रही है, तो कृपया ट्यूटोरियल लिंक की मदद लें।"
    )
    buttons = [
        [types.InlineKeyboardButton("💬 एडमिन से बात करें / Contact Admin", callback_data="ask_admin")]
    ]
    if TUTORIAL_URL:
        buttons.append([types.InlineKeyboardButton("❓ ट्यूटोरियल देखें / How to Verify", url=TUTORIAL_URL)])
    
    await message.reply_text(help_text, reply_markup=types.InlineKeyboardMarkup(buttons))

# लाइव चैट (ask_admin)
@Client.on_callback_query(filters.regex("ask_admin"))
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

# Myplan
@Client.on_message(filters.command("myplan"))
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

# Pricing
@Client.on_message(filters.command(["pricing", "plans"]))
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

# Start
@Client.on_message(filters.command("start"))
async def start(client, message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    is_admin = (user_id in ADMIN_IDS)
    
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

    # 🆕 यहाँ चेक किया जा रहा है कि यूजर पहले से डेटाबेस में है या नया है
    existing_user = await db.users.find_one({"user_id": user_id})
    
    await add_user(user_id)
    total_users = await db.users.count_documents({})
    
    # 🆕 अगर यूजर नया है, तभी लॉग चैनल में मैसेज जाएगा
    if not existing_user:
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
            asyncio.create_task(delete_album_after_delay(client, sent_msgs, warn_msg, 3600))
        except Exception as e:
            await message.reply(f"❌ एल्बम भेजने में एरर: {e}")
        return
        
    await message.reply(START_MESSAGE)
