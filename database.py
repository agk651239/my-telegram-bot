import time
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS

# MongoDB से जुड़ें
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

# 1. वेरिफिकेशन चेक करें
async def is_verified(user_id):
    if user_id in ADMIN_IDS: 
        return True
    user = await db.users.find_one({"user_id": user_id})
    return user is not None and user.get("expire_at", 0) > time.time()

# 2. वेरिफिकेशन सेट करें (24 घंटे के लिए)
async def set_verify(user_id):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"expire_at": time.time() + 86400}},
        upsert=True
    )

# 3. फाइल इंडेक्स (सेव) करें
async def add_file(file_data):
    # यह सुनिश्चित करता है कि फाइल आईडी डुप्लीकेट न हो
    await db.files.update_one(
        {"file_id": file_data["file_id"]},
        {"$set": file_data},
        upsert=True
    )

# 4. ब्रॉडकास्ट के लिए सभी यूजर आईडी निकालें
async def get_all_users():
    cursor = db.users.find({})
    return await cursor.to_list(length=None)

# 5. कुल यूजर्स की संख्या
async def get_total_users():
    return await db.users.count_documents({})
    
