import random
from typing import List, Optional
from datetime import datetime
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

        return True

    def explore_timeline(self, count: int = 5, update_user_profile_func=None):
        """بررسی پست‌های تایم‌لاین و تعامل با آن‌ها"""
        self.logger.info("بررسی تایم‌لاین")

        try:
            # دریافت فید تایم‌لاین
            feed_items = self.client.get_timeline_feed()
            self.logger.debug(f"Timeline feed type: {type(feed_items)}")

            # بررسی و تبدیل feed_items به یک لیست اگر نیست
            media_items = []
            if hasattr(feed_items, 'items'):
                # اگر feed_items یک شی با ویژگی items است
                media_items = feed_items.items
                self.logger.debug(
                    f"Feed items has 'items' attribute: {type(media_items)}")
            elif isinstance(feed_items, dict) and 'items' in feed_items:
                # اگر feed_items یک دیکشنری با کلید items است
                media_items = feed_items['items']
                self.logger.debug(
                    f"Feed items is dict with 'items' key: {type(media_items)}")
            elif isinstance(feed_items, list):
                # اگر feed_items قبلاً یک لیست است
                media_items = feed_items
                self.logger.debug(
                    f"Feed items is already a list: {len(media_items)}")
            else:
                self.logger.warning(
                    f"ساختار نامشخص برای feed_items: {type(feed_items)}")
                # اگر feed_items یک callable است (مانند یک متد)، آن را فراخوانی کنید
                if callable(feed_items):
                    try:
                        media_items = feed_items()
                        self.logger.debug(
                            f"Called feed_items as function: {type(media_items)}")
                    except Exception as e:
                        self.logger.error(
                            f"Error calling feed_items as function: {e}")
                # در صورت ساختار نامشخص، از یک لیست خالی استفاده می‌کنیم
                if not isinstance(media_items, list):
                    media_items = []

            self.logger.info(
                f"تعداد {len(media_items)} آیتم در تایم‌لاین یافت شد")

            # انتخاب تصادفی تعدادی از پست‌ها (اگر موارد کافی موجود باشند)
            if len(media_items) > 0:
                # محدود کردن تعداد انتخاب به حداکثر تعداد موارد موجود
                num_to_select = min(len(media_items), random.randint(1, 3))
                selected_items = random.sample(media_items, num_to_select)

                for item in selected_items:
                    try:
                        # بررسی ساختار آیتم
                        if hasattr(item, 'media_or_ad'):
                            media = item.media_or_ad
                        elif isinstance(item, dict) and 'media_or_ad' in item:
                            media = item['media_or_ad']
                        else:
                            self.logger.warning(
                                f"ساختار آیتم نامشخص است: {type(item)}")
                            continue

                        # استخراج اطلاعات کاربر
                        user_id = None
                        username = None

                        if hasattr(media, 'user'):
                            user_id = media.user.pk
                            username = media.user.username
                        elif isinstance(media, dict) and 'user' in media:
                            user_id = media['user']['pk']
                            username = media['user']['username']
                        else:
                            self.logger.warning("اطلاعات کاربر یافت نشد")
                            continue

                        # بررسی محتوای فارسی
                        has_persian = False
                        caption = None

                        if hasattr(media, 'caption') and media.caption:
                            caption = media.caption
                        elif isinstance(media, dict) and 'caption' in media and media['caption']:
                            caption = media['caption']

                        if caption:
                            has_persian = is_persian_content(caption)

                        # اولویت دادن به محتوای فارسی
                        if has_persian:
                            self.logger.info(
                                f"✅ محتوای فارسی در تایم‌لاین یافت شد: {caption[:30]}...")
                            # تعامل با محتوای فارسی
                            media_id = media.id if hasattr(
                                media, 'id') else media.get('id')
                            comment_result = self.actions.comment_on_media(
                                media_id, username, user_id, None, update_user_profile_func)
                        else:
                            # شانس کمتر برای تعامل با محتوای غیر فارسی
                            if random.random() < 0.2:  # 20% احتمال
                                media_id = media.id if hasattr(
                                    media, 'id') else media.get('id')
                                comment_result = self.actions.comment_on_media(
                                    media_id, username, user_id, None, update_user_profile_func)

                        # استراحت بین اکشن‌ها
                        human_sleep(15, 30)  # استراحت کوتاه‌تر

                    except Exception as e:
                        self.logger.error(
                            f"خطا در تعامل با رسانه تایم‌لاین: {e}")
                        import traceback
                        self.logger.error(traceback.format_exc())
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
                                self.actions.react_to_story(
                                    story.id, username, user_id, update_user_profile_func)

                                # افزایش شمارنده
                                user_count += 1
                                if user_count >= count:
                                    return True

                        # استراحت بین هر کاربر
                        human_sleep(15, 30)  # کاهش زمان استراحت

                    except Exception as e:
                        self.logger.error(
                            f"خطا در بررسی استوری‌های کاربر {user_id}: {e}")
            else:
                self.logger.warning(
                    f"لیست following نامعتبر است: {type(following)}")

            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.error("❌ چالش امنیتی در هنگام بررسی استوری‌ها")
                return False
            self.logger.error(f"خطا در بررسی استوری‌ها: {e}")
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
