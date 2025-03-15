import pymongo
from pymongo import MongoClient
from loguru import logger
import time
import sys

from app.config import MONGO_URI, MONGO_DB
from app.database.models import get_collection_name


def setup_logger():
    """تنظیم لاگر"""
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    logger.remove()  # حذف تنظیمات پیش‌فرض

    # افزودن خروجی کنسول
    logger.add(
        sys.stderr,
        format=log_format,
        level="DEBUG",
        colorize=True
    )

    return logger


def fix_ttl_indexes():
    """بررسی و حذف TTL ایندکس‌ها"""
    logger = setup_logger()

    try:
        # اتصال به مونگو
        logger.info(f"اتصال به مونگو: {MONGO_URI}")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client[MONGO_DB]

        # لیست کالکشن‌ها
        collections = db.list_collection_names()
        logger.info(f"کالکشن‌های یافت شده: {collections}")

        # کالکشن‌های اصلی
        interaction_collection = get_collection_name("interactions")
        sessions_collection = get_collection_name("sessions")
        users_collection = get_collection_name("users")
        stats_collection = get_collection_name("statistics")

        # بررسی هر کالکشن
        for collection_name in collections:
            collection = db[collection_name]

            # بررسی ایندکس‌ها
            indexes = list(collection.list_indexes())
            logger.info(
                f"کالکشن {collection_name} دارای {len(indexes)} ایندکس است")

            # جستجو برای TTL ایندکس
            ttl_found = False
            for index in indexes:
                index_info = index.to_dict()
                logger.info(f"ایندکس: {index_info}")

                # بررسی TTL
                if 'expireAfterSeconds' in index_info:
                    ttl_found = True
                    logger.warning(
                        f"ایندکس TTL در {collection_name} یافت شد: {index_info['name']}")

                    # حذف ایندکس
                    collection.drop_index(index_info['name'])
                    logger.info(f"ایندکس TTL حذف شد: {index_info['name']}")

            if not ttl_found:
                logger.info(
                    f"هیچ ایندکس TTL در کالکشن {collection_name} یافت نشد")

        # ایجاد ایندکس‌های مناسب بدون TTL
        logger.info("ایجاد ایندکس‌های کارآمد بدون TTL")

        # ایندکس برای interactions
        if interaction_collection in collections:
            db[interaction_collection].create_index(
                [("timestamp", pymongo.DESCENDING)])
            db[interaction_collection].create_index(
                [("user_id", pymongo.ASCENDING)])
            db[interaction_collection].create_index(
                [("username", pymongo.ASCENDING)])
            logger.info(
                f"ایندکس‌های کالکشن {interaction_collection} به‌روز شدند")

        # ایندکس برای sessions
        if sessions_collection in collections:
            db[sessions_collection].create_index(
                [("session_id", pymongo.ASCENDING)])
            db[sessions_collection].create_index(
                [("started_at", pymongo.DESCENDING)])
            logger.info(f"ایندکس‌های کالکشن {sessions_collection} به‌روز شدند")

        # ایندکس برای users
        if users_collection in collections:
            db[users_collection].create_index([("user_id", pymongo.ASCENDING)])
            db[users_collection].create_index(
                [("username", pymongo.ASCENDING)])
            logger.info(f"ایندکس‌های کالکشن {users_collection} به‌روز شدند")

        logger.info("عملیات بررسی و حذف TTL ایندکس‌ها با موفقیت انجام شد")
        return True

    except Exception as e:
        logger.error(f"خطا در بررسی و حذف TTL ایندکس‌ها: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    fix_ttl_indexes()
