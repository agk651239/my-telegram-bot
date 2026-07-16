import time
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

# MongoDB से जुड़ें
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

# 1. वेरिफिकेशन चेक करें (Admin हमेशा verified रहेगा)
async def is_verified(user_id):
    if user_id in ADMIN_IDS: 
        return True
    user = await db.users.find_one({"user_id": user_id})
    # अगर यूजर मौजूद है और उसका expire_at समय अभी के समय (time.time()) से ज्यादा है
    return user is not None and user.get("expire_at", 0) > time.time()

# 2. वेरिफिकेशन सेट करें (Config में दिए गए समय के अनुसार)
async def set_verify(user_id):
    expire_time = time.time() + VERIFY_EXPIRE_TIME
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"expire_at": expire_time}},
        upsert=True
    )

# 3. फाइल इंडेक्स (सेव) करें
async def add_file(file_data):
    await db.files.update_one(
        {"file_id": file_data["file_id"]},
        {"$set": file_data},
        upsert=True
    )

# 4. यूजर रजिस्टर करें (जब वो /start दबाए)
async def add_user(user_id):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

# 5. ब्रॉडकास्ट के लिए सभी यूजर्स निकालना
async def get_all_users():
    cursor = db.users.find({})
    return await cursor.to_list(length=None)

# 6. कुल यूजर्स की संख्या
async def get_total_users():
    return await db.users.count_documents({})

# 7. स्पेसिफिक यूजर का डेटाबेस से स्टेटस निकालने के लिए (Admin के /check कमांड हेतु)
async def get_user_data(user_id):
    return await db.users.find_one({"user_id": user_id})
    
