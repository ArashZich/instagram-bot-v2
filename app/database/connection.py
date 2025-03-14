from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from datetime import datetime, timedelta
import os
import time
import traceback
from app.config import MONGO_URI, MONGO_DB

# Singleton client
_mongo_client = None

# Create synchronous MongoDB client


def get_mongo_client():
    global _mongo_client

    # Return existing client if already connected
    if _mongo_client is not None:
        try:
            # Test connection
            _mongo_client.admin.command('ping')
            return _mongo_client
        except Exception:
            # Connection failed, reset and retry
            _mongo_client = None
            logger.warning("اتصال موجود به MongoDB قطع شده است، تلاش مجدد...")

    try:
        # وصل شدن به مونگو با تلاش مجدد
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(
                    f"Attempting to connect to MongoDB at {MONGO_URI} (attempt {retry_count+1}/{max_retries})")
                client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000,
                                     connectTimeoutMS=20000, socketTimeoutMS=20000)

                # چک کردن اتصال
                client.admin.command('ping')
                logger.info(f"✅ Connected to MongoDB at {MONGO_URI}")
                _mongo_client = client
                return client
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"⚠️ Attempt {retry_count}/{max_retries} failed to connect to MongoDB: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")

                if retry_count < max_retries:
                    # انتظار قبل از تلاش مجدد
                    wait_time = 5 * retry_count  # افزایش زمان انتظار با هر تلاش
                    logger.info(
                        f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    raise
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

# Get database


def get_database():
    try:
        client = get_mongo_client()
        if client:
            # تست اتصال و دسترسی‌ها
            db = client[MONGO_DB]
            # تست نوشتن در دیتابیس
            test_collection = db.get_collection("test_connection")
            test_id = test_collection.insert_one(
                {"test": True, "timestamp": datetime.now()}).inserted_id
            test_collection.delete_one({"_id": test_id})
            logger.info("✅ اتصال به MongoDB و تست نوشتن موفقیت‌آمیز بود")
            return db
        logger.error("❌ اتصال به MongoDB ناموفق بود")
        return None
    except Exception as e:
        logger.error(f"خطا در اتصال به دیتابیس: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

# Create asynchronous MongoDB client for FastAPI


async def get_async_database():
    try:
        client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        return client[MONGO_DB]
    except Exception as e:
        logger.error(f"Failed to connect to async MongoDB: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
