import time
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

# MongoDB से जुड़ें
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

# बोट स्टार्ट होते ही इंडेक्स बना दें ताकि सर्च हमेशा बिजली की रफ्तार से हो
async def create_indexes():
    """
    यह फंक्शन बोट स्टार्ट होते समय चलाया जाता है।
    यह डेटाबेस में इंडेक्स बनाता है जिससे सर्च की गति बढ़ जाती है।
    """
    try:
        await db.files.create_index("file_id", unique=True)
        await db.files.create_index("name") 
        await db.users.create_index("user_id", unique=True)
    except Exception as e:
        print(f"Index creation error: {e}")

# 1. वेरिफिकेशन चेक करें
async def is_verified(user_id):
    if user_id in ADMIN_IDS: return True
    user = await db.users.find_one({"user_id": user_id})
    # अगर यूजर मौजूद है और उसका वेरिफिकेशन समय अभी खत्म नहीं हुआ है
    return user is not None and user.get("expire_at", 0) > time.time()

# 2. वेरिफिकेशन सेट करें
async def set_verify(user_id):
    expire_time = time.time() + VERIFY_EXPIRE_TIME
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"expire_at": expire_time}},
        upsert=True
    )

# 3. फाइल इंडेक्स (सेव) करें - अपडेटेड
async def add_file(file_data):
    """
    फाइल सेव करने के लिए: file_id के आधार पर यूनिक एंट्री बनाएगा
    """
    if not file_data or "file_id" not in file_data:
        return
        
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

# 6. फाइल ढूंढना (ObjectId या file_id दोनों के लिए)
async def get_file_by_id(file_id_str):
    try:
        # अगर बटन से आया ObjectId है तो उसे ढूँढे
        return await db.files.find_one({"_id": ObjectId(file_id_str)})
    except:
        # अगर वह ObjectId नहीं है, तो file_id के आधार पर ढूँढे
        return await db.files.find_one({"file_id": file_id_str})
        
