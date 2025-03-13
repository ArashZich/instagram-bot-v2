from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
import os
import time
from app.config import MONGO_URI, MONGO_DB

# Create synchronous MongoDB client


def get_mongo_client():
    try:
        # وصل شدن به مونگو با تلاش مجدد
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(
                    f"Attempting to connect to MongoDB at {MONGO_URI} (attempt {retry_count+1}/{max_retries})")
                client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)

                # چک کردن اتصال
                client.admin.command('ping')
                logger.info(f"✅ Connected to MongoDB at {MONGO_URI}")
                return client
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"⚠️ Attempt {retry_count}/{max_retries} failed to connect to MongoDB: {e}")

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
        raise

# Get database


def get_database():
    client = get_mongo_client()
    return client[MONGO_DB]

# Create asynchronous MongoDB client for FastAPI


async def get_async_database():
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        return client[MONGO_DB]
    except Exception as e:
        logger.error(f"Failed to connect to async MongoDB: {e}")
        raise
