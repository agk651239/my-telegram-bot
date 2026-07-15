import time
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS

client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

async def is_verified(user_id):
    if user_id in ADMIN_IDS: return True
    user = await db.users.find_one({"user_id": user_id})
    return user and user.get("expire_at", 0) > time.time()

async def set_verify(user_id):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"expire_at": time.time() + 86400}},
        upsert=True
    )

async def add_file(file_data):
    await db.files.insert_one(file_data)
    
