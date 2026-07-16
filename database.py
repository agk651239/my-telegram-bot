import time
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

# MongoDB से जुड़ें
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

# 1. वेरिफिकेशन चेक करें
async def is_verified(user_id):
    if user_id in ADMIN_IDS: return True
    user = await db.users.find_one({"user_id": user_id})
    return user is not None and user.get("expire_at", 0) > time.time()

# 2. वेरिफिकेशन सेट करें
async def set_verify(user_id):
    expire_time = time.time() + VERIFY_EXPIRE_TIME
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"expire_at": expire_time}},
        upsert=True
    )

# 3. फाइल इंडेक्स (सेव) करें - अपडेटेड (size और thumb के लिए)
async def add_file(file_data):
    # अब यह file_size और thumb_id को भी अपडेट करेगा
    await db.files.update_one(
        {"file_id": file_data["file_id"]},
        {"$set": {
            "name": file_data["name"],
            "file_size": file_data.get("file_size", 0),
            "thumb_id": file_data.get("thumb_id"),
            "file_id": file_data["file_id"]
        }},
        upsert=True
    )

# 4. यूजर रजिस्टर करें
async def add_user(user_id):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

# 5. एडमिन के लिए यूजर डेटा निकालना
async def get_user_data(user_id):
    return await db.users.find_one({"user_id": user_id})

# 6. फाइल ढूंढना (ObjectId के लिए)
async def get_file_by_id(file_id_str):
    try:
        # callback_data में हम ObjectId स्ट्रिंग भेज रहे हैं, इसलिए यह बेस्ट है
        return await db.files.find_one({"_id": ObjectId(file_id_str)})
    except:
        # अगर कोई गलती होती है, तो सादी ID से चेक करें
        return await db.files.find_one({"file_id": file_id_str})
        
