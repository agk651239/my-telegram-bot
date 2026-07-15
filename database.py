import time
from motor.motor_asyncio import AsyncIOMotorClient
# यहाँ config से DATABASE_URI, DATABASE_NAME और ADMIN_IDS तीनों को साथ में import किया है
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS

# MongoDB से कनेक्शन बनाना
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]

# वेरिफिकेशन चेक करने का फंक्शन
async def is_verified(user_id):
    # अगर यूजर एडमिन है, तो हमेशा True (Bypass)
    if user_id in ADMIN_IDS: 
        return True
    
    # अगर एडमिन नहीं है, तो डेटाबेस में चेक करें
    user = await db.users.find_one({"user_id": user_id})
    return user and user.get("expire_at", 0) > time.time()

# यूजर को वेरीफाई करने का फंक्शन
async def set_verify(user_id):
    # 24 घंटे (86400 seconds) का टाइम जोड़कर सेव करना
    expiry_time = time.time() + 86400
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"expire_at": expiry_time}},
        upsert=True
    )

# फाइल डेटाबेस में स्टोर करने का फंक्शन
async def add_file(file_data):
    await db.files.insert_one(file_data)
    
