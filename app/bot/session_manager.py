import time
import random
import uuid
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError, ClientLoginRequired
import pickle
from loguru import logger
from pathlib import Path

from app.config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD
from app.database.connection import get_database
from app.database.models import BotSession, get_collection_name
from app.bot.utils import setup_logger, generate_session_id


class SessionManager:
    def __init__(self):
        self.client = Client()
        self.username = INSTAGRAM_USERNAME
        self.password = INSTAGRAM_PASSWORD
        self.db = get_database()
        self.logger = setup_logger()
        self.session_id = generate_session_id()
        self.logged_in = False
        self.last_error = None
        self.last_operation = "راه‌اندازی"

    def login(self) -> bool:
        """لاگین ساده به اینستاگرام"""
        try:
            if self.logged_in:
                return True

            self.logger.info(f"تلاش برای لاگین با کاربر {self.username}")
            self.last_operation = "لاگین به اینستاگرام"

            # بررسی وجود سشن قبلی
            session_path = Path("data/session.json")
            if session_path.exists():
                try:
                    self.logger.info("تلاش برای استفاده از سشن ذخیره شده...")
                    with open(session_path, "r") as f:
                        session_data = json.load(f)

                    self.client.set_settings(session_data)
                    self.client.get_timeline_feed()  # تست سشن

                    self.logged_in = True
                    self.logger.info("✅ استفاده از سشن قبلی موفقیت‌آمیز بود")
                    return True
                except Exception as se:
                    self.logger.warning(
                        f"⚠️ سشن قبلی معتبر نیست، لاگین مجدد: {se}")

            # تنظیم پارامترهای کلاینت و لاگین
            self.client.delay_range = [3, 8]
            self.client.request_timeout = 90

            self.logger.info("در حال اجرای لاگین...")
            login_result = self.client.login(self.username, self.password)
            self.logger.info(f"نتیجه لاگین: {login_result}")

            if login_result:
                # ذخیره سشن برای استفاده آینده
                session_path.parent.mkdir(exist_ok=True)
                with open(session_path, "w") as f:
                    json.dump(self.client.get_settings(), f)

                self.logged_in = True
                self.logger.info("✅ ورود موفقیت‌آمیز به اینستاگرام")
                return True
            else:
                self.logger.error("❌ لاگین ناموفق بود")
                return False

        except Exception as e:
            self.logged_in = False
            self.logger.error(f"❌ خطا در لاگین: {str(e)}")
            self.last_error = str(e)
            import traceback
            traceback.print_exc()
            return False

    def record_session_start(self):
        """ثبت شروع سشن در دیتابیس"""
        session = BotSession(
            session_id=self.session_id,
            started_at=datetime.now(),
            user_agent="instagrapi-client",
            session_data={
                "username": self.username,
                "device_id": self.client.device_id if hasattr(self.client, "device_id") else None
            },
            is_active=True
        )

        self.db[get_collection_name("sessions")].insert_one(session.to_dict())
        self.logger.info(f"Recorded session start with ID: {self.session_id}")

    def record_session_end(self):
        """ثبت پایان سشن در دیتابیس"""
        self.db[get_collection_name("sessions")].update_one(
            {"session_id": self.session_id},
            {
                "$set": {
                    "ended_at": datetime.now(),
                    "is_active": False
                }
            }
        )
        self.logger.info(f"Recorded session end with ID: {self.session_id}")

    def handle_challenge(self, e):
        """مدیریت چالش‌های اینستاگرام"""
        self.logger.warning(f"⚠️ چالش اینستاگرام تشخیص داده شد: {e}")

        # ریست کردن کلاینت
        self.logged_in = False

        # بازگشت False برای اطلاع‌رسانی به متدهای دیگر
        return False
