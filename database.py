import time
import logging
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

# लॉगिंग सेटअप
logger = logging.getLogger(__name__)

# MongoDB कनेक्शन
try:
    client = AsyncIOMotorClient(DATABASE_URI)
    db = client[DATABASE_NAME]
    logger.info("✅ डेटाबेस से सफलतापूर्वक जुड़ गए।")
except Exception as e:
    logger.error(f"❌ डेटाबेस कनेक्शन एरर: {e}")

# इंडेक्स बनाना (बोट की सर्चिंग स्पीड बढ़ाने के लिए जरूरी है)
async def create_indexes():
    try:
        await db.files.create_index("file_id", unique=True)
        await db.files.create_index("name")
        await db.users.create_index("user_id", unique=True)
        logger.info("✅ डेटाबेस इंडेक्स तैयार हैं।")
    except Exception as e:
        logger.error(f"❌ इंडेक्स क्रिएशन एरर: {e}")

# वेरिफिकेशन चेक करना (24 घंटे वाला लॉजिक)
async def is_verified(user_id):
    if user_id in ADMIN_IDS: 
        return True
    try:
        user = await db.users.find_one({"user_id": user_id})
        # अगर यूजर डेटाबेस में है और expire_at अभी के समय से ज्यादा है
        if user and user.get("expire_at"):
            return user["expire_at"] > time.time()
        return False
    except Exception as e: 
        logger.error(f"❌ वेरिफिकेशन चेक एरर: {e}")
        return False

# वेरिफिकेशन सेट करना (24 घंटे का समय जोड़ने के लिए)
async def set_verify(user_id):
    try:
        expire_time = time.time() + VERIFY_EXPIRE_TIME
        await db.users.update_one(
            {"user_id": user_id}, 
            {"$set": {"expire_at": expire_time}}, 
            upsert=True
        )
    except Exception as e: 
        logger.error(f"❌ वेरिफिकेशन सेट करने में एरर: {e}")

# फाइल को डेटाबेस में जोड़ना (message_id के साथ)
async def add_file(d):
    if not d or "file_id" not in d: 
        return
    try:
        await db.files.update_one(
            {"file_id": d["file_id"]}, 
            {"$set": {
                "name": d["name"], 
                "file_size": d.get("file_size", 0), 
                "thumb_id": d.get("thumb_id"), 
                "file_id": d["file_id"],
                "message_id": d.get("message_id")
            }}, 
            upsert=True
        )
    except Exception as e: 
        logger.error(f"❌ फाइल ऐड/इंडेक्सिंग एरर: {e}")

# यूजर को डेटाबेस में जोड़ना
async def add_user(user_id):
    try: 
        await db.users.update_one(
            {"user_id": user_id}, 
            {"$set": {"user_id": user_id}}, 
            upsert=True
        )
    except Exception as e: 
        logger.error(f"❌ यूजर ऐड एरर: {e}")

# फाइल को आईडी या _id से ढूंढना (Unique Link के लिए)
async def get_file_by_id(fid):
    try:
        # यहाँ ObjectId का उपयोग किया गया है ताकि लिंक से डायरेक्ट फाइल मिल सके
        query = {"_id": ObjectId(fid)} if ObjectId.is_valid(fid) else {"file_id": fid}
        return await db.files.find_one(query)
    except Exception as e:
        logger.error(f"❌ फाइल फेच एरर: {e}")
        return None
        
