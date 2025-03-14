import random
from typing import List, Optional
from datetime import datetime
import json
from loguru import logger

from app.bot.utils import human_sleep, is_persian_content, setup_logger


class InstagramExplorers:
    def __init__(self, client, actions, db=None):
        self.client = client
        self.actions = actions
        self.db = db
        self.logger = setup_logger()

    def explore_hashtags(self, hashtags: List[str], count: int = 5, update_user_profile_func=None):
        """جستجوی پست‌ها با هشتگ‌های مشخص و تعامل با آن‌ها"""
        for hashtag in hashtags:
            self.logger.info(f"🔍 جستجوی هشتگ: #{hashtag}")

            try:
                # دریافت پست‌ها براساس هشتگ
                self.logger.info(f"در حال دریافت پست‌های اخیر برای #{hashtag}")
                medias = self.client.hashtag_medias_recent(hashtag, count)
                self.logger.info(
                    f"تعداد {len(medias)} پست برای #{hashtag} یافت شد")

                # تعامل تصادفی با تعدادی از پست‌ها (نه همه آنها)
                if len(medias) > 0:
                    # محدود کردن تعداد انتخاب به حداکثر تعداد موارد موجود
                    num_to_select = min(len(medias), random.randint(1, 3))
                    selected_medias = random.sample(medias, num_to_select)

                    for i, media in enumerate(selected_medias):
                        try:
                            user_id = media.user.pk
                            username = media.user.username

                            self.logger.info(
                                f"پست {i+1}/{len(selected_medias)}: تعامل با پست @{username}")

                            # بررسی محتوای فارسی
                            has_persian = False
                            if hasattr(media, 'caption') and media.caption:
                                has_persian = is_persian_content(media.caption)

                            # اولویت دادن به محتوای فارسی
                            if has_persian:
                                self.logger.info(
                                    f"✅ محتوای فارسی یافت شد: {media.caption[:30] if media.caption else ''}...")
                                # تعامل با محتوای فارسی
                                if update_user_profile_func is None:
                                    self.logger.warning(
                                        "تابع update_user_profile_func مشخص نشده است!")
                                    # در اینجا می‌توانید یک تابع پیش‌فرض یا یک مقدار برگشتی برای جلوگیری از خطا قرار دهید

                                comment_result = self.actions.comment_on_media(
                                    media.id, username, user_id, hashtag, update_user_profile_func)

                                if comment_result:
                                    self.logger.info(
                                        f"✅ نظر با موفقیت برای @{username} ثبت شد")
                            else:
                                # شانس کمتر برای تعامل با محتوای غیر فارسی
                                if random.random() < 0.3:  # 30% احتمال
                                    comment_result = self.actions.comment_on_media(
                                        media.id, username, user_id, hashtag, update_user_profile_func)
                                    if comment_result:
                                        self.logger.info(
                                            f"✅ نظر با موفقیت برای @{username} ثبت شد")

                            # استراحت بین اکشن‌ها
                            human_sleep(15, 30)  # استراحت کوتاه‌تر بین اکشن‌ها

                        except Exception as e:
                            self.logger.error(
                                f"❌ خطا در تعامل با رسانه {media.id}: {e}")
                            import traceback
                            self.logger.error(
                                f"Traceback: {traceback.format_exc()}")

                    # استراحت کوتاه‌تر بین هر هشتگ
                    sleep_time = random.randint(30, 60)  # 30 ثانیه تا 1 دقیقه
                    self.logger.info(
                        f"⏱ استراحت به مدت {sleep_time} ثانیه قبل از هشتگ بعدی")
                    human_sleep(sleep_time)
                else:
                    self.logger.warning(
                        f"هیچ پستی برای هشتگ {hashtag} یافت نشد")

            except Exception as e:
                if "challenge_required" in str(e).lower():
                    self.logger.error(
                        f"❌ چالش امنیتی در هنگام جستجوی هشتگ {hashtag}")
                    return False
                self.logger.error(f"❌ خطا در جستجوی هشتگ {hashtag}: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")

        return True

    def explore_timeline(self, count: int = 5, update_user_profile_func=None):
        """بررسی پست‌های تایم‌لاین و تعامل با آن‌ها"""
        self.logger.info("بررسی تایم‌لاین")

        try:
            # رویکرد جدید: استفاده از متدهای جایگزین برای دریافت فید
            # روش ۱: استفاده از get_timeline_feed به عنوان یک تابع
            try:
                self.logger.info("تلاش برای دریافت تایم‌لاین با روش اول")
                if callable(self.client.get_timeline_feed):
                    feed_items = self.client.get_timeline_feed()
                    self.logger.info(
                        f"نوع feed_items با روش اول: {type(feed_items)}")
                else:
                    self.logger.warning(
                        "get_timeline_feed یک تابع قابل فراخوانی نیست!")
                    feed_items = []
            except Exception as e:
                self.logger.warning(f"خطا در دریافت تایم‌لاین با روش اول: {e}")
                feed_items = []

            # بررسی نتیجه اولیه
            if not feed_items or (isinstance(feed_items, list) and len(feed_items) == 0):
                # روش ۲: استفاده از user_medias برای فید
                try:
                    self.logger.info("تلاش برای دریافت مدیا با روش دوم")
                    user_id = self.client.user_id
                    feed_items = self.client.user_medias(
                        user_id, 20)  # دریافت 20 پست اخیر کاربر
                    self.logger.info(
                        f"تعداد آیتم‌های یافت شده با روش دوم: {len(feed_items) if isinstance(feed_items, list) else 'غیر لیست'}")
                except Exception as e:
                    self.logger.warning(f"خطا در دریافت مدیا با روش دوم: {e}")
                    feed_items = []

            # بررسی نتیجه دوم
            if not feed_items or (isinstance(feed_items, list) and len(feed_items) == 0):
                # روش ۳: استفاده از hashtag_medias_recent برای دریافت پست‌های اخیر یک هشتگ عمومی
                try:
                    self.logger.info(
                        "تلاش برای دریافت پست‌های هشتگ با روش سوم")
                    from app.config import PERSIAN_HASHTAGS
                    import random

                    # انتخاب یک هشتگ تصادفی
                    hashtag = random.choice(PERSIAN_HASHTAGS)
                    self.logger.info(
                        f"استفاده از هشتگ {hashtag} برای جایگزینی تایم‌لاین")

                    feed_items = self.client.hashtag_medias_recent(hashtag, 10)
                    self.logger.info(
                        f"تعداد آیتم‌های یافت شده با روش سوم: {len(feed_items) if isinstance(feed_items, list) else 'غیر لیست'}")
                except Exception as e:
                    self.logger.warning(
                        f"خطا در دریافت پست‌های هشتگ با روش سوم: {e}")
                    feed_items = []

            # اطمینان از اینکه feed_items یک لیست است
            if not isinstance(feed_items, list):
                self.logger.warning(
                    f"feed_items یک لیست نیست، تبدیل به لیست خالی: {type(feed_items)}")
                media_items = []
            else:
                media_items = feed_items

            self.logger.info(
                f"تعداد {len(media_items)} آیتم در تایم‌لاین یافت شد")

            # انتخاب تصادفی تعدادی از پست‌ها (اگر موارد کافی موجود باشند)
            if len(media_items) > 0:
                # محدود کردن تعداد انتخاب به حداکثر تعداد موارد موجود
                num_to_select = min(len(media_items), random.randint(1, 3))
                selected_items = random.sample(media_items, num_to_select)

                for item in selected_items:
                    try:
                        # در روش‌های مختلف، ساختار متفاوتی داریم
                        media = item  # در روش‌های 2 و 3 معمولاً خود آیتم، مدیا است

                        # بررسی ساختار آیتم
                        if hasattr(item, 'media_or_ad'):
                            media = item.media_or_ad
                        elif isinstance(item, dict) and 'media_or_ad' in item:
                            media = item['media_or_ad']

                        # لاگ اطلاعات مدیا برای عیب‌یابی
                        self.logger.debug(f"نوع آیتم مدیا: {type(media)}")
                        if hasattr(media, '__dict__'):
                            self.logger.debug(
                                f"ویژگی‌های آیتم مدیا: {dir(media)[:10]}")

                        # استخراج اطلاعات کاربر
                        user_id = None
                        username = None

                        if hasattr(media, 'user'):
                            user_id = media.user.pk
                            username = media.user.username
                        elif isinstance(media, dict) and 'user' in media:
                            user_id = media['user']['pk']
                            username = media['user']['username']
                        elif hasattr(media, 'user_id'):
                            # دریافت اطلاعات کاربر با user_id موجود
                            user_id = media.user_id
                            try:
                                user_info = self.client.user_info(user_id)
                                username = user_info.username
                            except Exception as e:
                                self.logger.warning(
                                    f"خطا در دریافت اطلاعات کاربر: {e}")
                                continue
                        else:
                            self.logger.warning(
                                f"اطلاعات کاربر یافت نشد: {type(media)}")
                            continue

                        # بررسی محتوای فارسی
                        has_persian = False
                        caption = None

                        if hasattr(media, 'caption') and media.caption:
                            caption = media.caption
                        elif isinstance(media, dict) and 'caption' in media and media['caption']:
                            caption = media['caption']
                        elif hasattr(media, 'caption_text') and media.caption_text:
                            caption = media.caption_text

                        if caption:
                            self.logger.debug(f"کپشن پست: {caption[:50]}")
                            has_persian = is_persian_content(caption)

                        # اولویت دادن به محتوای فارسی
                        if has_persian:
                            self.logger.info(
                                f"✅ محتوای فارسی در تایم‌لاین یافت شد: {caption[:30] if caption else ''}...")

                            # تعامل با محتوای فارسی
                            media_id = None
                            if hasattr(media, 'id'):
                                media_id = media.id
                            elif isinstance(media, dict) and 'id' in media:
                                media_id = media['id']
                            elif hasattr(media, 'pk'):
                                media_id = media.pk

                            if media_id:
                                self.logger.info(
                                    f"تلاش برای کامنت گذاشتن روی پست با شناسه {media_id}")
                                comment_result = self.actions.comment_on_media(
                                    media_id, username, user_id, None, update_user_profile_func)

                                if comment_result:
                                    self.logger.info(
                                        f"✅ کامنت با موفقیت ارسال شد")
                                else:
                                    self.logger.warning(
                                        f"❌ خطا در ارسال کامنت")
                            else:
                                self.logger.warning(f"❌ شناسه مدیا یافت نشد")
                        else:
                            # شانس کمتر برای تعامل با محتوای غیر فارسی
                            if random.random() < 0.2:  # 20% احتمال
                                media_id = None
                                if hasattr(media, 'id'):
                                    media_id = media.id
                                elif isinstance(media, dict) and 'id' in media:
                                    media_id = media['id']
                                elif hasattr(media, 'pk'):
                                    media_id = media.pk

                                if media_id:
                                    comment_result = self.actions.comment_on_media(
                                        media_id, username, user_id, None, update_user_profile_func)

                        # استراحت بین اکشن‌ها
                        human_sleep(15, 30)  # استراحت کوتاه‌تر

                    except Exception as e:
                        self.logger.error(
                            f"خطا در تعامل با رسانه تایم‌لاین: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())

                return True
            else:
                self.logger.warning("هیچ پستی در تایم‌لاین یافت نشد")
                return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.error("❌ چالش امنیتی در هنگام بررسی تایم‌لاین")
                return False
            self.logger.error(f"خطا در بررسی تایم‌لاین: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def check_stories(self, count: int = 3, update_user_profile_func=None):
        """بررسی و واکنش به استوری‌ها"""
        self.logger.info("بررسی استوری‌ها")

        try:
            # دریافت لیست افرادی که دنبال می‌کنیم
            following = self.client.user_following(self.client.user_id)

            # بررسی اگر following یک دیکشنری است
            if isinstance(following, dict) and following:
                # انتخاب تصادفی چند کاربر
                selected_users = list(following.keys())
                random.shuffle(selected_users)
                # حداکثر تعداد محدودی کاربر انتخاب می‌کنیم
                selected_users = selected_users[:min(5, len(selected_users))]

                user_count = 0
                error_count = 0  # شمارنده خطا برای محدود کردن تلاش‌های ناموفق

                for user_id in selected_users:
                    try:
                        # دریافت اطلاعات کاربر
                        user_info = self.client.user_info(user_id)
                        username = user_info.username

                        self.logger.info(f"بررسی استوری‌های کاربر: {username}")

                        # دریافت استوری‌های کاربر
                        stories = self.client.user_stories(user_id)

                        if stories:
                            # شانس تصادفی برای واکنش
                            if random.random() < 0.4:  # 40% احتمال
                                self.logger.info(
                                    f"تعداد {len(stories)} استوری برای {username} یافت شد")

                                # انتخاب یک استوری تصادفی
                                story = random.choice(stories)

                                # واکنش به استوری
                                reaction_result = self.actions.react_to_story(
                                    story.id, username, user_id, update_user_profile_func)

                                if reaction_result:
                                    # افزایش شمارنده
                                    user_count += 1
                                    self.logger.info(
                                        f"✅ واکنش به استوری {username} موفقیت‌آمیز بود")
                                else:
                                    self.logger.warning(
                                        f"⚠️ واکنش به استوری {username} ناموفق بود")
                                    error_count += 1

                                if user_count >= count:
                                    self.logger.info(
                                        f"به تعداد کافی ({count}) استوری واکنش نشان داده شد")
                                    return True

                        # استراحت بین هر کاربر
                        human_sleep(15, 30)  # کاهش زمان استراحت

                        # اگر تعداد خطاها از حد مشخصی بیشتر شد، از حلقه خارج شو
                        if error_count >= 3:
                            self.logger.warning(
                                "تعداد خطاها بیش از حد مجاز است، خروج از حلقه")
                            return False

                    except json.JSONDecodeError as je:
                        self.logger.warning(
                            f"❌ خطای JSONDecodeError در بررسی استوری‌های کاربر {user_id}: {je}")
                        error_count += 1

                        # اگر تعداد خطاهای JSON بیش از حد است، خارج شو
                        if error_count >= 3:
                            self.logger.error(
                                "تعداد خطاهای JSON بیش از حد مجاز است، خروج از تابع")
                            return False

                        # استراحت طولانی‌تر در صورت خطای JSON
                        human_sleep(20, 40)
                        continue

                    except Exception as e:
                        self.logger.error(
                            f"خطا در بررسی استوری‌های کاربر {user_id}: {e}")
                        error_count += 1

                        # اگر خطای چالش امنیتی رخ داده، زودتر خارج شو
                        if "challenge_required" in str(e).lower():
                            self.logger.error(
                                "چالش امنیتی تشخیص داده شد، خروج از تابع")
                            return False

                        # اگر تعداد خطاها بیش از حد است، خارج شو
                        if error_count >= 3:
                            self.logger.error(
                                "تعداد خطاها بیش از حد مجاز است، خروج از تابع")
                            return False

                # اگر به هر دلیلی از حلقه خارج شدیم ولی تعداد کافی تعامل نداشتیم
                self.logger.info(
                    f"پایان بررسی استوری‌ها. تعداد واکنش‌ها: {user_count}")
                return user_count > 0  # اگر حداقل یک واکنش داشتیم، موفق محسوب می‌شود

            else:
                self.logger.warning(
                    f"لیست following نامعتبر است: {type(following)}")
                return False

        except json.JSONDecodeError as je:
            self.logger.error(f"❌ خطای JSONDecodeError در سطح اصلی تابع: {je}")
            return False
        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.error("❌ چالش امنیتی در هنگام بررسی استوری‌ها")
                return False
            self.logger.error(f"خطا در بررسی استوری‌ها: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def interact_with_followers(self, count: int = 2, update_user_profile_func=None):
        """تعامل با دنبال‌کنندگان از طریق ارسال پیام‌های مستقیم"""
        self.logger.info("تعامل با دنبال‌کنندگان")

        try:
            from app.database.models import get_collection_name
            from datetime import timedelta

            # دریافت دنبال‌کنندگانی که اخیراً با آن‌ها پیام نداشته‌ایم
            followers = self.db[get_collection_name("users")].find({
                "is_follower": True,
                "$or": [
                    # یک هفته (کاهش از دو هفته)
                    {"last_interaction": {"$lt": datetime.now() - timedelta(days=7)}},
                    {"last_interaction": {"$exists": False}}
                ]
            }).limit(10)  # دریافت تعداد بیشتری برای انتخاب تصادفی

            followers_list = list(followers)
            if not followers_list:
                self.logger.info("دنبال‌کننده‌ای برای تعامل یافت نشد")
                return True

            # انتخاب تصادفی تعدادی از دنبال‌کنندگان
            selected_followers = random.sample(
                followers_list, min(len(followers_list), count))

            for follower in selected_followers:
                user_id = follower["user_id"]
                username = follower["username"]

                # ارسال پیام مستقیم با شانس کم
                if random.random() < 0.3:  # 30% احتمال
                    self.actions.send_direct_message(
                        user_id, username, "appreciation", update_user_profile_func)

                # استراحت کوتاه‌تر بین هر پیام
                human_sleep(30, 60)  # 30-60 ثانیه استراحت

            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.error(
                    "❌ چالش امنیتی در هنگام تعامل با دنبال‌کنندگان")
                return False
            self.logger.error(f"خطا در تعامل با دنبال‌کنندگان: {e}")
            return False
