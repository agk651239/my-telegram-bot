import time
import logging
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

# लॉगिंग सेटअप
logger = logging.getLogger(__name__)

# MongoDB कनेक्शन
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

# इंडेक्स बनाना (एरर से बचने के लिए पुराने इंडेक्स को हटाकर नया बनाने वाला लॉजिक)
async def create_indexes():
    try:
        # अगर पुराना 'name_text' इंडेक्स मौजूद है, तो उसे हटाएं ताकि नया इंडेक्स बिना एरर बने
        try:
            await db.files.drop_index("name_text")
        except:
            pass
            
        # नाम पर टेक्स्ट इंडेक्स
        await db.files.create_index([("name", "text")], default_language='none')
        # यूजर आईडी के लिए इंडेक्स
        await db.users.create_index("user_id", unique=True)
        # फाइल के लिए यूनिक इंडेक्स ताकि एक ही फाइल बार-बार न जुड़े
        try:
            await db.files.create_index("file_id", unique=True)
        except:
            pass
        logger.info("✅ डेटाबेस इंडेक्स सफलतापूर्वक तैयार हैं।")
    except Exception as e:
        logger.error(f"❌ इंडेक्स क्रिएशन एरर: {e}")

# वेरिफिकेशन चेक करना
async def is_verified(user_id):
    if user_id in ADMIN_IDS: 
        return True
    try:
        user = await db.users.find_one({"user_id": user_id})
        if user and user.get("expire_at"):
            return user["expire_at"] > time.time()
        return False
    except Exception as e: 
        logger.error(f"❌ वेरिफिकेशन चेक एरर: {e}")
        return False

# वेरिफिकेशन सेट करना
async def set_verify(user_id):
    try:
        expire_time = time.time() + VERIFY_EXPIRE_TIME
        await db.users.update_one(
            {"user_id": user_id}, 
            {"$set": {"expire_at": expire_time}}, 
            upsert=True
        )
    except Exception as e: 
        logger.error(f"❌ वेरिफिकेशन अपडेट एरर: {e}")

# फाइल को डेटाबेस में जोड़ना (duplicate handling add kiya hai)
async def add_file(d):
    if not d or "file_id" not in d: 
        return
    try:
        # update_one ka use kiya hai upsert=True ke saath, isse duplicate entry nahi banegi
        await db.files.update_one(
            {"file_id": d.get("file_id")},
            {"$set": {
                "name": d.get("name"), 
                "file_type": d.get("file_type"), 
                "file_size": d.get("file_size", 0), 
                "thumb_id": d.get("thumb_id"), 
                "message_id": d.get("message_id"),
                "media_group_id": d.get("media_group_id"), # Ye field album ke liye zaroori hai
                "created_at": time.time()
            }},
            upsert=True
        )
        logger.info(f"✅ फाइल सेव या अपडेट हुई: {d.get('name')}")
    except Exception as e: 
        logger.error(f"❌ फाइल ऐड करने में एरर: {e}")

# यूजर को डेटाबेस में जोड़ना
async def add_user(user_id):
    try: 
        await db.users.update_one(
            {"user_id": user_id}, 
            {"$setOnInsert": {"user_id": user_id, "created_at": time.time()}}, 
            upsert=True
        )
    except Exception as e: 
        logger.error(f"❌ यूजर ऐड एरर: {e}")

# फाइल को आईडी या _id से ढूंढना
async def get_file_by_id(fid):
    try:
        # अगर fid एक वैध ObjectId है (जो सर्च से मिलेगा)
        if ObjectId.is_valid(fid):
            return await db.files.find_one({"_id": ObjectId(fid)})
        # अन्यथा file_id से सर्च करें
        return await db.files.find_one({"file_id": fid})
    except Exception as e:
        logger.error(f"❌ फाइल फेच एरर: {e}")
        return None
        
