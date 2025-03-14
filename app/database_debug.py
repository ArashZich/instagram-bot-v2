#!/usr/bin/env python
# app/database_debug.py

from app.database.models import get_collection_name
from app.database.connection import get_database
import sys
import os
from datetime import datetime
from loguru import logger

# تنظیم مسیر برای واردسازی ماژول‌های پروژه
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_logger():
    """تنظیم لاگر برای دیباگ"""
    logger.remove()  # حذف هندلرهای پیش‌فرض
    logger.add(sys.stdout, level="DEBUG")  # اضافه کردن هندلر خروجی استاندارد
    logger.add("logs/database_debug_{time}.log",
               level="DEBUG")  # اضافه کردن هندلر فایل
    return logger


def check_database_connection():
    """بررسی اتصال به دیتابیس"""
    logger.info("در حال بررسی اتصال به دیتابیس...")
    try:
        db = get_database()
        if db:
            logger.success("✅ اتصال به دیتابیس برقرار است.")
            return db
        else:
            logger.error("❌ خطا در اتصال به دیتابیس!")
            return None
    except Exception as e:
        logger.error(f"❌ خطا در اتصال به دیتابیس: {e}")
        return None


def check_collections(db):
    """بررسی کالکشن‌های موجود در دیتابیس"""
    logger.info("در حال بررسی کالکشن‌های دیتابیس...")
    collections = db.list_collection_names()
    logger.info(f"کالکشن‌های موجود: {collections}")

    # بررسی کالکشن‌های مورد نیاز
    required_collections = [
        get_collection_name("sessions"),
        get_collection_name("interactions"),
        get_collection_name("users"),
        get_collection_name("statistics")
    ]

    for collection in required_collections:
        if collection in collections:
            logger.success(f"✅ کالکشن {collection} موجود است.")
        else:
            logger.warning(f"⚠️ کالکشن {collection} یافت نشد!")


def check_collection_data(db, collection_key, limit=10):
    """بررسی داده‌های موجود در یک کالکشن"""
    collection_name = get_collection_name(collection_key)
    logger.info(f"در حال بررسی داده‌های کالکشن {collection_name}...")

    try:
        count = db[collection_name].count_documents({})
        logger.info(f"تعداد سندهای موجود در {collection_name}: {count}")

        if count > 0:
            # نمایش چند سند اول
            logger.info(f"نمونه سندهای موجود در {collection_name}:")
            for doc in db[collection_name].find().limit(limit):
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])  # تبدیل ObjectId به رشته
                logger.info(f"سند: {doc}")
        else:
            logger.warning(f"⚠️ کالکشن {collection_name} خالی است!")
    except Exception as e:
        logger.error(f"❌ خطا در بررسی داده‌های کالکشن {collection_name}: {e}")


def insert_test_interaction(db):
    """تلاش برای درج یک تعامل آزمایشی"""
    logger.info("در حال درج تعامل آزمایشی...")

    from app.database.models import UserInteraction, InteractionType

    try:
        # ایجاد یک تعامل آزمایشی
        test_interaction = UserInteraction(
            user_id="test_user_id",
            username="test_username",
            interaction_type=InteractionType.COMMENT,
            timestamp=datetime.now(),
            content="این یک تعامل آزمایشی است",
            status="success",
            metadata={"test": True, "source": "database_debug"}
        )

        # تبدیل به دیکشنری
        interaction_dict = test_interaction.to_dict()

        # درج در دیتابیس
        collection_name = get_collection_name("interactions")
        result = db[collection_name].insert_one(interaction_dict)

        if result.inserted_id:
            logger.success(
                f"✅ تعامل آزمایشی با موفقیت درج شد. ID: {result.inserted_id}")

            # بررسی بازیابی
            saved = db[collection_name].find_one({"_id": result.inserted_id})
            if saved:
                logger.success("✅ تعامل آزمایشی با موفقیت بازیابی شد.")
            else:
                logger.error("❌ خطا در بازیابی تعامل آزمایشی!")
        else:
            logger.error("❌ خطا در درج تعامل آزمایشی!")
    except Exception as e:
        logger.error(f"❌ خطا در درج تعامل آزمایشی: {e}")
        import traceback
        logger.error(f"جزئیات خطا: {traceback.format_exc()}")


if __name__ == "__main__":
    # راه‌اندازی لاگر
    logger = setup_logger()
    logger.info("=== شروع دیباگ دیتابیس ===")

    # بررسی اتصال به دیتابیس
    db = check_database_connection()

    if db:
        # بررسی کالکشن‌ها
        check_collections(db)

        # بررسی داده‌های هر کالکشن
        check_collection_data(db, "sessions")
        check_collection_data(db, "interactions")
        check_collection_data(db, "users")

        # تست درج داده
        insert_test_interaction(db)

    logger.info("=== پایان دیباگ دیتابیس ===")
