import time
import logging
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

# लॉगिंग सेट करें
logger = logging.getLogger(__name__)

# MongoDB से जुड़ें
try:
    client = AsyncIOMotorClient(DATABASE_URI)
    db = client[DATABASE_NAME]
    logger.info("Database connected successfully.")
except Exception as e:
    logger.error(f"Database connection failed: {e}")

# बोट स्टार्ट होते ही इंडेक्स बना दें
async def create_indexes():
    """
    यह फंक्शन बोट स्टार्ट होते समय चलाया जाता है।
    """
    try:
        await db.files.create_index("file_id", unique=True)
        await db.files.create_index("name") 
        await db.users.create_index("user_id", unique=True)
        logger.info("Database indexes created/verified.")
    except Exception as e:
        logger.error(f"Index creation error: {e}")

# 1. वेरिफिकेशन चेक करें
async def is_verified(user_id):
    if user_id in ADMIN_IDS: return True
    try:
        user = await db.users.find_one({"user_id": user_id})
        return user is not None and user.get("expire_at", 0) > time.time()
    except Exception as e:
        logger.error(f"Error checking verification for {user_id}: {e}")
        return False

# 2. वेरिफिकेशन सेट करें
async def set_verify(user_id):
    expire_time = time.time() + VERIFY_EXPIRE_TIME
    try:
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"expire_at": expire_time}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error setting verification for {user_id}: {e}")

# 3. फाइल इंडेक्स (सेव) करें
async def add_file(file_data):
    if not file_data or "file_id" not in file_data:
        return
        
    try:
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
    except Exception as e:
        logger.error(f"Error adding file {file_data.get('file_id')}: {e}")

# 4. यूजर रजिस्टर करें
async def add_user(user_id):
    try:
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")

# 5. एडमिन के लिए यूजर डेटा निकालना
async def get_user_data(user_id):
    try:
        return await db.users.find_one({"user_id": user_id})
    except Exception as e:
        logger.error(f"Error fetching user data {user_id}: {e}")
        return None

# 6. फाइल ढूंढना (ObjectId या file_id दोनों के लिए)
async def get_file_by_id(file_id_str):
    try:
        if ObjectId.is_valid(file_id_str):
            return await db.files.find_one({"_id": ObjectId(file_id_str)})
        else:
            return await db.files.find_one({"file_id": file_id_str})
    except Exception as e:
        logger.error(f"Error fetching file by id {file_id_str}: {e}")
        return None
        
