from pyrogram import Client, filters, types
import logging
from config import ADMIN_ID, UPI_ID, ADMIN_IDS
from database import db, get_plan_prices, get_qr_code

# --- 1. प्रीमियम मेनू (बटन कॉलबैक) ---
@Client.on_callback_query(filters.regex("buy_premium_menu"))
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

# --- 2. प्लान सेलेक्ट करने पर (QR कोड और UPI आईडी) ---
@Client.on_callback_query(filters.regex(r"^buyplan_"))
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

# --- 3. "मैंने पेमेंट कर दिया है" बटन ---
@Client.on_callback_query(filters.regex(r"^paid_"))
async def user_paid_cb(client, callback_query):
    plan_key = callback_query.data.split("paid_")[1]
    
    # तुरंत डेटाबेस में सही प्लान अपडेट करें
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

# --- 4. पेमेंट स्क्रीनशॉट हैंडलर (एडमिन को भेजना) ---
@Client.on_message(filters.photo)
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
