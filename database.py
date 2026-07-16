import time, logging
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME, ADMIN_IDS, VERIFY_EXPIRE_TIME

logger = logging.getLogger(__name__)

try:
    client = AsyncIOMotorClient(DATABASE_URI)
    db = client[DATABASE_NAME]
    logger.info("Database connected.")
except Exception as e:
    logger.error(f"DB Error: {e}")

async def create_indexes():
    try:
        await db.files.create_index("file_id", unique=True)
        await db.files.create_index("name")
        await db.users.create_index("user_id", unique=True)
        logger.info("Indexes ready.")
    except Exception as e:
        logger.error(f"Index Error: {e}")

async def is_verified(user_id):
    if user_id in ADMIN_IDS: return True
    try:
        u = await db.users.find_one({"user_id": user_id})
        return u is not None and u.get("expire_at", 0) > time.time()
    except: return False

async def set_verify(user_id):
    try:
        await db.users.update_one({"user_id": user_id}, {"$set": {"expire_at": time.time() + VERIFY_EXPIRE_TIME}}, upsert=True)
    except Exception as e: logger.error(f"Verify Error: {e}")

async def add_file(d):
    if not d or "file_id" not in d: return
    try:
        await db.files.update_one({"file_id": d["file_id"]}, {"$set": {"name": d["name"], "file_size": d.get("file_size", 0), "thumb_id": d.get("thumb_id"), "file_id": d["file_id"]}}, upsert=True)
    except Exception as e: logger.error(f"File Add Error: {e}")

async def add_user(user_id):
    try: await db.users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    except Exception as e: logger.error(f"User Add Error: {e}")

async def get_user_data(user_id):
    try: return await db.users.find_one({"user_id": user_id})
    except: return None

async def get_file_by_id(fid):
    try:
        q = {"_id": ObjectId(fid)} if ObjectId.is_valid(fid) else {"file_id": fid}
        return await db.files.find_one(q)
    except Exception as e:
        logger.error(f"Fetch File Error: {e}")
        return None


