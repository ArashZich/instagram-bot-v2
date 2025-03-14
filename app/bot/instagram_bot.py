import time
import random
import threading
import traceback
import schedule
from datetime import datetime, timedelta
from loguru import logger
import json
from pathlib import Path

from app.config import (
    DAILY_INTERACTION_LIMIT,
    PERSIAN_HASHTAGS,
    get_random_interval,
    get_random_session_duration,
    get_random_break_duration
)
from app.database.connection import get_database
from app.database.models import UserProfile, get_collection_name
from app.bot.utils import setup_logger, human_sleep
from app.bot.session_manager import SessionManager
from app.bot.actions import InstagramActions
from app.bot.explorers import InstagramExplorers


class InstagramBot(SessionManager):
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.daily_interactions = 0
        self.last_check_follower_time = datetime.now()
        self.session_start_time = datetime.now()
        self.session_end_time = self.session_start_time + \
            timedelta(seconds=get_random_session_duration())

        # ایجاد کلاس‌های کمکی
        self.actions = InstagramActions(self.client, self.db, self.session_id)
        self.explorers = InstagramExplorers(self.client, self.actions, self.db)
        # اضافه کردن ارجاع به دیتابیس برای explorer
        self.explorers.db = self.db

        # ایجاد کالکشن‌ها اگر وجود ندارند
        self._initialize_collections()

    def _initialize_collections(self):
        """ایجاد کالکشن‌های دیتابیس در صورت عدم وجود"""
        collections = self.db.list_collection_names()
        required_collections = [
            get_collection_name("sessions"),
            get_collection_name("interactions"),
            get_collection_name("users"),
            get_collection_name("statistics")
        ]

        for collection in required_collections:
            if collection not in collections:
                self.db.create_collection(collection)
                self.logger.info(f"ایجاد کالکشن: {collection}")

    def _update_user_profile(self, user_id: str, username: str, interaction_type: str):
        """به‌روزرسانی یا ایجاد پروفایل کاربر در دیتابیس"""
        from app.database.models import get_collection_name, UserProfile
        from app.database.connection import get_database

        try:
            # اطمینان از اتصال به دیتابیس
            if self.db is None:
                self.logger.error(
                    "اتصال به دیتابیس در _update_user_profile برقرار نیست، تلاش مجدد...")
                self.db = get_database()
                if self.db is None:
                    self.logger.error("نمی‌توان به دیتابیس متصل شد!")
                    return False

            # تعیین نام کالکشن
            collection_name = get_collection_name("users")
            self.logger.info(
                f"بررسی پروفایل کاربر {username} در کالکشن {collection_name}")

            # بررسی وجود کالکشن و ایجاد آن در صورت نیاز
            collections = self.db.list_collection_names()
            if collection_name not in collections:
                self.logger.warning(
                    f"کالکشن {collection_name} وجود ندارد، در حال ایجاد...")
                self.db.create_collection(collection_name)

            # جستجوی کاربر در دیتابیس
            user_data = self.db[collection_name].find_one({"user_id": user_id})

            # تابع برای پاکسازی داده‌ها قبل از ذخیره در مونگو
            def sanitize_dict(obj):
                if isinstance(obj, dict):
                    return {key: sanitize_dict(value) for key, value in obj.items() if key != "_id"}
                elif isinstance(obj, list):
                    return [sanitize_dict(item) for item in list(obj)]
                elif isinstance(obj, datetime):
                    return obj  # حفظ اشیاء تاریخ بدون تغییر
                elif hasattr(obj, "dict") and callable(getattr(obj, "dict")):
                    # پشتیبانی از مدل‌های Pydantic یا اشیاء مشابه
                    return sanitize_dict(obj.dict())
                elif hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
                    # پشتیبانی از متدهای to_dict سفارشی
                    return sanitize_dict(obj.to_dict())
                else:
                    return obj

            if user_data:
                # به‌روزرسانی پروفایل موجود
                self.logger.info(
                    f"پروفایل کاربر {username} یافت شد، در حال بروزرسانی...")

                try:
                    # ایجاد داده‌های به‌روزرسانی
                    update_data = {
                        "$set": {
                            "last_interaction": datetime.now(),
                            "username": username  # اطمینان از به‌روز بودن نام کاربری
                        },
                        "$inc": {
                            "interaction_count": 1
                        }
                    }

                    # اضافه کردن نوع تعامل به لیست اگر وجود ندارد
                    update_data["$addToSet"] = {
                        "metadata.interaction_types": interaction_type
                    }

                    # اجرای عملیات به‌روزرسانی
                    update_result = self.db[collection_name].update_one(
                        {"user_id": user_id},
                        update_data
                    )

                    # بررسی نتیجه به‌روزرسانی
                    if update_result.modified_count > 0:
                        self.logger.info(
                            f"پروفایل کاربر {username} با موفقیت به‌روزرسانی شد")
                    else:
                        self.logger.warning(
                            f"پروفایل کاربر {username} تغییر نکرد. matched_count={update_result.matched_count}")

                    # برای اطمینان، بررسی کنیم که آیا پروفایل به درستی به‌روزرسانی شده است
                    updated_user = self.db[collection_name].find_one(
                        {"user_id": user_id})
                    if updated_user:
                        self.logger.info(
                            f"بررسی پروفایل به‌روزرسانی شده: interaction_count={updated_user.get('interaction_count', 'N/A')}")
                    else:
                        self.logger.warning(
                            "پروفایل پس از به‌روزرسانی یافت نشد!")

                except Exception as update_error:
                    self.logger.error(
                        f"خطا در بروزرسانی پروفایل: {update_error}")
                    self.logger.error(f"traceback: {traceback.format_exc()}")
                    # حتی در صورت خطا، ادامه می‌دهیم تا حداقل تعامل ثبت شود
            else:
                # ایجاد پروفایل کاربر جدید
                self.logger.info(
                    f"پروفایل کاربر {username} یافت نشد، در حال ایجاد پروفایل جدید...")

                # تلاش برای دریافت اطلاعات کاربر
                user_info = None
                try:
                    user_info = self.client.user_info_by_username(username)
                    self.logger.debug(
                        f"اطلاعات کاربر {username} دریافت شد: {type(user_info)}")
                except Exception as e:
                    self.logger.warning(
                        f"خطا در دریافت اطلاعات کاربر {username}: {e}")

                # آماده‌سازی دیکشنری اطلاعات کاربر
                user_info_dict = {}
                if user_info:
                    try:
                        # تبدیل به دیکشنری بر اساس آنچه در دسترس است
                        if hasattr(user_info, "dict") and callable(getattr(user_info, "dict")):
                            user_info_dict = sanitize_dict(user_info.dict())
                        elif hasattr(user_info, "to_dict") and callable(getattr(user_info, "to_dict")):
                            user_info_dict = sanitize_dict(user_info.to_dict())
                        elif hasattr(user_info, "__dict__"):
                            user_info_dict = sanitize_dict(user_info.__dict__)

                        # حذف فیلدهای غیرضروری که ممکن است خطا ایجاد کنند
                        if "_id" in user_info_dict:
                            del user_info_dict["_id"]
                    except Exception as e:
                        self.logger.error(
                            f"خطا در تبدیل user_info به دیکشنری: {e}")
                        self.logger.error(
                            f"traceback: {traceback.format_exc()}")

                # تعیین اینکه آیا کاربر فالور است یا ما او را فالو کرده‌ایم
                is_follower = False
                is_following = False

                try:
                    # دریافت دنبال‌کنندگان و دنبال‌شوندگان
                    followers = self.client.user_followers(self.client.user_id)
                    following = self.client.user_following(self.client.user_id)

                    # بررسی وضعیت کاربر
                    if isinstance(followers, dict):
                        is_follower = user_id in followers.keys()

                    if isinstance(following, dict):
                        is_following = user_id in following.keys()

                    self.logger.info(
                        f"وضعیت کاربر {username}: فالوئر={is_follower}, فالوئینگ={is_following}")
                except Exception as e:
                    self.logger.warning(
                        f"خطا در بررسی وضعیت فالو کاربر {username}: {e}")

                # ایجاد پروفایل کاربر جدید
                current_time = datetime.now()
                user_profile = UserProfile(
                    user_id=user_id,
                    username=username,
                    full_name=user_info.full_name if user_info and hasattr(
                        user_info, "full_name") else None,
                    is_following=is_following,
                    is_follower=is_follower,
                    interaction_count=1,
                    last_interaction=current_time,
                    first_seen=current_time,
                    metadata={
                        "interaction_types": [interaction_type],
                        "user_info": user_info_dict
                    }
                )

                # تبدیل به دیکشنری و پاکسازی
                user_profile_dict = sanitize_dict(user_profile.to_dict())

                # لاگ داده‌های پروفایل برای دیباگ
                self.logger.debug(
                    f"داده‌های پروفایل کاربر برای درج: {json.dumps(user_profile_dict, default=str)[:1000]}...")

                try:
                    # درج در دیتابیس
                    result = self.db[collection_name].insert_one(
                        user_profile_dict)

                    if result.inserted_id:
                        self.logger.info(
                            f"پروفایل کاربر {username} با ID {result.inserted_id} ایجاد شد")

                        # بررسی موفقیت درج
                        inserted_doc = self.db[collection_name].find_one(
                            {"_id": result.inserted_id})
                        if inserted_doc:
                            self.logger.info(
                                f"پروفایل با موفقیت درج شد و بازیابی شد")
                        else:
                            self.logger.warning(
                                f"پروفایل درج شد اما بازیابی نشد!")
                    else:
                        self.logger.warning(
                            f"پروفایل کاربر {username} درج نشد!")
                except Exception as insert_error:
                    self.logger.error(
                        f"خطا در درج پروفایل کاربر: {insert_error}")
                    self.logger.error(f"traceback: {traceback.format_exc()}")

            return True

        except Exception as e:
            import traceback
            self.logger.error(
                f"خطا در به‌روزرسانی پروفایل کاربر (traceback): {traceback.format_exc()}")
            self.logger.error(f"خطا در به‌روزرسانی پروفایل کاربر: {e}")
            return False

    def check_and_update_followers(self):
        """بررسی دنبال‌کنندگان جدید و به‌روزرسانی دیتابیس"""
        if (datetime.now() - self.last_check_follower_time).total_seconds() < 3600:  # کاهش به 1 ساعت
            # بررسی بیش از هر 1 ساعت انجام نمی‌شود
            return True

        self.logger.info("بررسی دنبال‌کنندگان و دنبال‌شوندگان")

        try:
            # دریافت دنبال‌کنندگان و دنبال‌شوندگان فعلی
            followers = self.client.user_followers(self.client.user_id)
            following = self.client.user_following(self.client.user_id)

            if not isinstance(followers, dict) or not isinstance(following, dict):
                self.logger.warning(
                    f"فرمت نامعتبر برای followers/following: followers {type(followers)}, following {type(following)}")
                return True

            followers_set = set(followers.keys())
            following_set = set(following.keys())

            # به‌روزرسانی دیتابیس
            for user_id in followers_set.union(following_set):
                is_follower = user_id in followers_set
                is_following = user_id in following_set

                # تلاش برای دریافت نام کاربری
                username = None
                try:
                    user_info = self.client.user_info(user_id)
                    username = user_info.username
                except Exception as e:
                    self.logger.warning(
                        f"Could not fetch username for user {user_id}: {e}")

                if not username:
                    continue

                # به‌روزرسانی دیتابیس
                existing_user = self.db[get_collection_name(
                    "users")].find_one({"user_id": user_id})

                if existing_user:
                    # به‌روزرسانی کاربر موجود
                    self.db[get_collection_name("users")].update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "is_follower": is_follower,
                            "is_following": is_following
                        }}
                    )

                    # اگر کاربر دیگر ما را دنبال نمی‌کند اما ما او را دنبال می‌کنیم، لغو دنبال کردن
                    if not is_follower and is_following and existing_user.get("is_follower", False):
                        # به جای لغو فوری، با احتمال کمتر
                        if random.random() < 0.3:  # 30% احتمال
                            self.logger.info(
                                f"کاربر {username} ما را آنفالو کرده، آنفالو می‌کنیم")
                            self.actions.unfollow_user(
                                user_id, username, self._update_user_profile)

                    # اگر کاربر ما را دنبال کرده و ما او را دنبال نمی‌کنیم، دنبال کردن
                    elif is_follower and not is_following and not existing_user.get("is_follower", False):
                        # با احتمال متوسط
                        if random.random() < 0.5:  # 50% احتمال
                            self.logger.info(
                                f"دنبال‌کننده جدید {username}، فالو بک می‌دهیم")
                            self.actions.follow_user(
                                user_id, username, self._update_user_profile)
                else:
                    # ایجاد پروفایل کاربر جدید
                    user_profile = UserProfile(
                        user_id=user_id,
                        username=username,
                        is_following=is_following,
                        is_follower=is_follower,
                        interaction_count=0,
                        metadata={}
                    )

                    self.db[get_collection_name("users")].insert_one(
                        user_profile.to_dict())

                    # اگر دنبال‌کننده جدید است، با احتمال متوسط دنبال کردن
                    if is_follower and not is_following:
                        if random.random() < 0.5:  # 50% احتمال
                            self.logger.info(
                                f"دنبال‌کننده جدید {username}، فالو بک می‌دهیم")
                            self.actions.follow_user(
                                user_id, username, self._update_user_profile)

                # استراحت بین هر کاربر برای طبیعی بودن
                human_sleep(1, 3)  # کاهش زمان استراحت بین کاربران

            self.last_check_follower_time = datetime.now()
            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.error(f"چالش امنیتی در هنگام بررسی دنبال‌کنندگان")
                # درصورت چالش امنیتی، تلاش مجدد برای لاگین
                if not self.login():
                    self.logger.error("لاگین مجدد ناموفق بود")
                    return False
                else:
                    self.logger.info("لاگین مجدد موفقیت‌آمیز بود")
                    return True

            self.logger.error(f"خطا در بررسی دنبال‌کنندگان: {e}")
            traceback.print_exc()
            return False

    def reset_daily_interactions(self):
        """بازنشانی شمارنده تعاملات روزانه"""
        self.daily_interactions = 0
        self.logger.info("بازنشانی شمارنده تعاملات روزانه")

    def _handle_challenge(self, e):
        """مدیریت چالش‌های اینستاگرام"""
        self.logger.warning(f"⚠️ چالش اینستاگرام تشخیص داده شد: {e}")

        # تلاش برای لاگین مجدد قبل از استراحت طولانی
        if self.login():
            self.logger.info("✅ لاگین مجدد موفقیت‌آمیز بود")
            # استراحت کوتاه
            human_sleep(60, 120)  # 1-2 دقیقه
            return True

        # ریست کردن کلاینت
        self.logged_in = False

        # استراحت متوسط (کوتاه‌تر از قبل)
        medium_break = random.randint(600, 1200)  # 10-20 دقیقه
        self.logger.info(
            f"⏸ استراحت متوسط برای حفظ امنیت اکانت: {medium_break//60} دقیقه")

        # پایان دادن به سشن فعلی
        self.record_session_end()
        self.is_running = False

        return False

    def run_session(self):
        """اجرای یک جلسه بات با استراحت‌های طبیعی"""
        # تنظیم تایم‌اوت لاگین
        login_start_time = datetime.now()
        login_timeout = 120  # 2 دقیقه تایم‌اوت

        self.logger.info(f"⏱ تنظیم تایم‌اوت لاگین به {login_timeout} ثانیه")

        if not self.login():
            self.logger.error("❌ لاگین ناموفق بود، نمی‌توان بات را شروع کرد")
            return

        login_duration = (datetime.now() - login_start_time).total_seconds()
        self.logger.info(f"⏱ فرآیند لاگین {login_duration:.2f} ثانیه طول کشید")

        self.is_running = True
        self.session_start_time = datetime.now()
        self.session_end_time = self.session_start_time + \
            timedelta(seconds=get_random_session_duration())

        self.logger.info(
            f"📅 شروع جلسه بات: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')} تا {self.session_end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # ثبت شروع جلسه
        self.record_session_start()

        # محدودیت اکشن در هر ساعت
        hourly_action_limit = 10  # افزایش از 5 به 10 اکشن در ساعت
        hourly_actions = 0
        last_hour_reset = datetime.now()

        # حلقه اصلی بات
        while self.is_running and datetime.now() < self.session_end_time:
            try:
                # بررسی ریست محدودیت ساعتی
                if (datetime.now() - last_hour_reset).total_seconds() > 3600:
                    hourly_actions = 0
                    last_hour_reset = datetime.now()
                    self.logger.info("🕒 بازنشانی شمارنده اکشن‌های ساعتی")

                # بررسی محدودیت ساعتی
                if hourly_actions >= hourly_action_limit:
                    sleep_time = random.randint(
                        300, 600)  # استراحت 5-10 دقیقه
                    self.logger.info(
                        f"⚠️ محدودیت اکشن ساعتی رسیده ({hourly_actions}/{hourly_action_limit})، استراحت به مدت {sleep_time} ثانیه")
                    human_sleep(sleep_time)
                    continue

                # بررسی اگر به محدودیت تعامل روزانه رسیده‌ایم
                if self.daily_interactions >= DAILY_INTERACTION_LIMIT:
                    self.logger.info(
                        f"⚠️ محدودیت تعامل روزانه رسیده ({self.daily_interactions}/{DAILY_INTERACTION_LIMIT})، استراحت")
                    human_sleep(600, 900)  # استراحت 10-15 دقیقه
                    continue

                # بررسی و به‌روزرسانی دنبال‌کنندگان/دنبال‌شوندگان
                self.logger.info("🔄 بررسی وضعیت دنبال‌کنندگان و دنبال‌شوندگان")
                follower_check_result = self.check_and_update_followers()

                if not follower_check_result:
                    self.logger.warning(
                        "مشکل در بررسی دنبال‌کنندگان، تلاش مجدد")
                    # تلاش مجدد برای لاگین با استراحت کوتاه
                    human_sleep(60, 120)
                    if not self.login():
                        self.logger.error("لاگین مجدد ناموفق، پایان جلسه")
                        break
                    self.logger.info("لاگین مجدد موفقیت‌آمیز، ادامه جلسه")
                    # کوتاه‌تر کردن جلسه فعلی
                    current_time = datetime.now()
                    remaining_time = (self.session_end_time -
                                      current_time).total_seconds()
                    # نصف کردن زمان باقیمانده
                    self.session_end_time = current_time + \
                        timedelta(seconds=max(300, remaining_time/2))
                    self.logger.info(
                        f"زمان جلسه کوتاه شد، پایان جدید: {self.session_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    continue

                # انتخاب تصادفی یک اکشن براساس اولویت‌ها و زمان روز
                # وزن‌های بیشتر برای اکشن‌های کم خطرتر
                action = random.choices(
                    ["explore_hashtags", "explore_timeline",
                        "check_stories", "interact_with_followers"],
                    # وزن‌های تنظیم شده برای کاهش اکشن‌های پرخطر
                    weights=[0.35, 0.30, 0.25, 0.10],
                    k=1
                )[0]

                self.logger.info(f"🎯 اکشن انتخاب شده: {action}")

                action_result = False

                if action == "explore_hashtags":
                    # انتخاب هشتگ‌های فارسی برای جستجو
                    selected_hashtags = random.sample(PERSIAN_HASHTAGS, 2)
                    self.logger.info(f"🔍 جستجوی هشتگ‌ها: {selected_hashtags}")
                    # تعداد کمتر برای تعامل در هر هشتگ
                    action_result = self.explorers.explore_hashtags(selected_hashtags, count=random.randint(
                        1, 2), update_user_profile_func=self._update_user_profile)

                elif action == "explore_timeline":
                    self.logger.info("📱 بررسی تایم‌لاین")
                    # تعداد کمتر برای تعامل در تایم‌لاین
                    action_result = self.explorers.explore_timeline(count=random.randint(
                        1, 2), update_user_profile_func=self._update_user_profile)

                elif action == "check_stories":
                    self.logger.info("📊 بررسی استوری‌ها")
                    # تعداد کمتر برای تعامل با استوری‌ها
                    action_result = self.explorers.check_stories(count=random.randint(
                        1, 2), update_user_profile_func=self._update_user_profile)

                elif action == "interact_with_followers":
                    self.logger.info("👥 تعامل با دنبال‌کنندگان")
                    # فقط 1 یا 2 نفر در هر جلسه
                    action_result = self.explorers.interact_with_followers(
                        count=random.randint(1, 2), update_user_profile_func=self._update_user_profile)

                # اگر چالش امنیتی رخ داده، تلاش مجدد برای لاگین
                if action_result is False:
                    self.logger.warning(
                        "نتیجه اکشن منفی بود، احتمال چالش امنیتی")
                    # تلاش مجدد برای لاگین با استراحت کوتاه
                    human_sleep(30, 60)
                    if not self.login():
                        self.logger.error("لاگین مجدد ناموفق، پایان جلسه")
                        break
                    else:
                        self.logger.info(
                            "لاگین مجدد موفقیت‌آمیز، ادامه با اکشن دیگر")
                        # کوتاه‌تر کردن جلسه فعلی
                        current_time = datetime.now()
                        remaining_time = (
                            self.session_end_time - current_time).total_seconds()
                        # نصف کردن زمان باقیمانده
                        self.session_end_time = current_time + \
                            timedelta(seconds=max(300, remaining_time/2))
                        self.logger.info(
                            f"زمان جلسه کوتاه شد، پایان جدید: {self.session_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        continue

                # افزایش شمارنده اکشن‌های ساعتی
                hourly_actions += 1

                # استراحت طبیعی بین گروه‌های اکشن
                sleep_duration = get_random_interval()
                self.logger.info(
                    f"⏱ استراحت به مدت {sleep_duration} ثانیه")
                human_sleep(sleep_duration, sleep_duration + 30)

                # ثبت آمار فعلی
                self.logger.info(
                    f"📊 آمار فعلی: {self.daily_interactions}/{DAILY_INTERACTION_LIMIT} تعامل امروز")

            except Exception as e:
                self.logger.error(f"❌ خطا در حلقه بات: {e}")
                traceback.print_exc()
                human_sleep(120, 180)  # استراحت 2-3 دقیقه در صورت خطا

        # پایان جلسه
        self.record_session_end()
        self.is_running = False
        self.logger.info("✅ جلسه بات پایان یافت")

        # زمان‌بندی جلسه بعدی پس از استراحت
        break_duration = get_random_break_duration()
        next_session_time = datetime.now() + timedelta(seconds=break_duration)
        self.logger.info(
            f"⏭️ جلسه بعدی در {next_session_time.strftime('%Y-%m-%d %H:%M:%S')} زمان‌بندی شد")

    def run_continuously(self):
        """اجرای مداوم بات با جلسات طبیعی و استراحت‌ها"""
        def _worker():
            # زمان‌بندی بازنشانی روزانه در نیمه‌شب
            schedule.every().day.at("00:00").do(self.reset_daily_interactions)

            while True:
                try:
                    # اجرای وظایف زمان‌بندی شده
                    schedule.run_pending()

                    # اگر در حال اجرا نیست، شروع جلسه جدید
                    if not self.is_running:
                        self.logger.info("🔄 شروع جلسه جدید بات...")

                        try:
                            self.run_session()
                        except Exception as e:
                            self.logger.error(f"❌ خطا در جلسه: {e}")
                            traceback.print_exc()
                            self.is_running = False
                            # کاهش زمان انتظار از 5 دقیقه به 2 دقیقه قبل از تلاش مجدد
                            time.sleep(120)

                        # پس از پایان جلسه، استراحت قبل از جلسه بعدی
                        break_duration = get_random_break_duration()
                        self.logger.info(
                            f"⏸ استراحت به مدت {break_duration/60:.1f} دقیقه")
                        human_sleep(break_duration, break_duration + 120)

                    time.sleep(1)

                except Exception as e:
                    self.logger.error(f"❌ خطا در ترد کارگر: {e}")
                    traceback.print_exc()
                    time.sleep(30)  # کاهش از 60 به 30 ثانیه

        # شروع ترد کارگر
        worker_thread = threading.Thread(target=_worker)
        worker_thread.daemon = True
        worker_thread.start()

        self.logger.info("🤖 بات در حالت مداوم شروع شد")
        return worker_thread

    def stop(self):
        """توقف بات"""
        self.is_running = False
        self.record_session_end()
        self.logger.info("بات متوقف شد")
