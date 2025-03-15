import random
from typing import List, Optional
from datetime import datetime
import json
from loguru import logger

from app.bot.utils import human_sleep, is_persian_content, setup_logger


def custom_search_tags(client, tag):
    """Custom implementation to search tags when the native method is not available"""
    try:
        # Try using the hashtag_info method
        return client.hashtag_info(tag)
    except Exception as e:
        logger.warning(f"Error using hashtag_info: {e}")
        return None


class InstagramExplorers:
    def __init__(self, client, actions, db=None):
        self.client = client
        self.actions = actions
        self.db = db
        self.logger = setup_logger()

        # Add search_tags if not present
        if not hasattr(self.client, 'search_tags'):
            self.logger.info("Adding custom search_tags method to client")
            self.client.search_tags = lambda tag: custom_search_tags(
                self.client, tag)

    def explore_hashtags(self, hashtags: List[str], count: int = 5, update_user_profile_func=None):
        """جستجوی پست‌ها با هشتگ‌های مشخص و تعامل با آن‌ها"""
        for hashtag in hashtags:
            self.logger.info(f"🔍 جستجوی هشتگ: #{hashtag}")

            try:
                # استفاده از روش جایگزین برای جستجوی هشتگ
                medias = []

                # روش 0: تلاش با hashtag_medias_recent اگر وجود داشته باشد
                try:
                    if hasattr(self.client, 'hashtag_medias_recent'):
                        self.logger.info(
                            f"تلاش برای دریافت پست‌های اخیر هشتگ #{hashtag}")
                        medias = self.client.hashtag_medias_recent(
                            hashtag, count)
                        if medias:
                            self.logger.info(
                                f"دریافت {len(medias)} پست با hashtag_medias_recent")
                except Exception as e:
                    self.logger.warning(f"خطا در دریافت پست‌های اخیر: {e}")

                # اگر روش قبلی موفق نبود، تلاش با روش دیگر
                if not medias:
                    try:
                        # روش 1: استفاده از جستجوی عمومی به جای هشتگ مستقیم
                        self.logger.info(
                            f"تلاش برای یافتن پست‌های هشتگ #{hashtag} با روش جستجو")

                        search_results = self.client.search_tags(hashtag)
                        if search_results:
                            # اگر هشتگ پیدا شد، سعی می‌کنیم از طریق پروفایل آن به پست‌ها دسترسی پیدا کنیم
                            tag_id = search_results.id if hasattr(
                                search_results, 'id') else None

                            if tag_id:
                                # تلاش برای دریافت پست‌های مرتبط با هشتگ
                                try:
                                    tag_info = self.client.hashtag_info(
                                        hashtag)
                                    if hasattr(tag_info, 'media_count') and tag_info.media_count > 0:
                                        # می‌توانیم از top posts استفاده کنیم
                                        medias = self.client.hashtag_medias_top(
                                            hashtag, count)
                                        self.logger.info(
                                            f"پست‌های برتر هشتگ #{hashtag} دریافت شدند")
                                except Exception as e:
                                    self.logger.warning(
                                        f"خطا در دریافت اطلاعات هشتگ: {e}")
                    except Exception as tag_error:
                        self.logger.warning(
                            f"خطا در جستجوی هشتگ با روش اول: {tag_error}")

                # روش 2: استفاده از جستجوی عمومی
                if not medias:
                    try:
                        self.logger.info("تلاش با روش جستجوی عمومی")
                        search_result = self.search_posts(hashtag)
                        medias = search_result[:count] if search_result else []
                        if medias:
                            self.logger.info(
                                f"تعداد {len(medias)} پست با جستجوی عمومی یافت شد")
                    except Exception as search_error:
                        self.logger.warning(
                            f"خطا در جستجوی عمومی: {search_error}")

                # روش 3: استفاده از پست‌های فالوئینگ‌ها یا explore
                if not medias:
                    try:
                        self.logger.info(
                            "تلاش برای یافتن محتوای مرتبط از سایر منابع")
                        medias = self.find_alternative_content(
                            [hashtag], count)
                        if medias:
                            self.logger.info(
                                f"تعداد {len(medias)} پست جایگزین یافت شد")
                    except Exception as alt_error:
                        self.logger.warning(
                            f"خطا در یافتن محتوای جایگزین: {alt_error}")

                # تعامل با پست‌های یافت شده
                if len(medias) > 0:
                    # محدود کردن تعداد انتخاب به حداکثر تعداد موارد موجود
                    num_to_select = min(len(medias), random.randint(1, 3))
                    selected_medias = random.sample(medias, num_to_select)

                    for i, media in enumerate(selected_medias):
                        try:
                            # استخراج اطلاعات کاربر از مدیا
                            user_id = None
                            username = None

                            # پشتیبانی از فرمت‌های مختلف مدیا
                            if hasattr(media, 'user'):
                                user_id = media.user.pk
                                username = media.user.username
                            elif isinstance(media, dict) and 'user' in media:
                                user_id = media['user']['pk']
                                username = media['user']['username']
                            elif hasattr(media, 'user_id'):
                                user_id = media.user_id
                                try:
                                    user_info = self.client.user_info(user_id)
                                    username = user_info.username
                                except Exception as e:
                                    # اگر نتوانستیم اطلاعات کاربر را دریافت کنیم، ادامه می‌دهیم
                                    self.logger.warning(
                                        f"خطا در دریافت اطلاعات کاربر: {e}")
                                    continue
                            else:
                                # اگر نتوانستیم اطلاعات کاربر را پیدا کنیم، ادامه می‌دهیم
                                self.logger.warning(
                                    f"اطلاعات کاربر یافت نشد: {type(media)}")
                                continue

                            self.logger.info(
                                f"پست {i+1}/{len(selected_medias)}: تعامل با پست از @{username}")

                            # بررسی محتوای فارسی
                            has_persian = False
                            caption = None

                            # پشتیبانی از فرمت‌های مختلف برای کپشن
                            if hasattr(media, 'caption') and media.caption:
                                caption = media.caption
                            elif isinstance(media, dict) and 'caption' in media and media['caption']:
                                caption = media['caption']
                            elif hasattr(media, 'caption_text') and media.caption_text:
                                caption = media.caption_text

                            # تبدیل کپشن به رشته
                            caption_text = ""
                            if caption:
                                # تبدیل caption به رشته قبل از استفاده
                                if isinstance(caption, str):
                                    caption_text = caption[:50]
                                elif isinstance(caption, dict):
                                    caption_text = str(caption)[:50]
                                else:
                                    caption_text = str(caption)[:50]

                            self.logger.debug(f"کپشن پست: {caption_text}")

                            if caption:
                                if isinstance(caption, str):
                                    has_persian = is_persian_content(caption)
                                else:
                                    has_persian = is_persian_content(
                                        str(caption))

                            # اولویت دادن به محتوای فارسی
                            if has_persian:
                                self.logger.info(
                                    f"✅ محتوای فارسی یافت شد: {caption_text}...")

                                # تعامل با محتوای فارسی
                                media_id = None
                                if hasattr(media, 'id'):
                                    media_id = media.id
                                elif isinstance(media, dict) and 'id' in media:
                                    media_id = media['id']
                                elif hasattr(media, 'pk'):
                                    media_id = media.pk
                                elif isinstance(media, dict) and 'pk' in media:
                                    media_id = media['pk']

                                if media_id:
                                    if update_user_profile_func is None:
                                        self.logger.warning(
                                            "تابع update_user_profile_func مشخص نشده است!")
                                        # یک تابع پیش‌فرض خالی

                                        def update_user_profile_dummy(user_id, username, interaction_type):
                                            self.logger.debug(
                                                f"تابع پیش‌فرض update_user_profile برای {username}")
                                            return True
                                        update_user_profile_func = update_user_profile_dummy

                                    comment_result = self.actions.comment_on_media(
                                        media_id, username, user_id, hashtag, update_user_profile_func)

                                    if comment_result:
                                        self.logger.info(
                                            f"✅ نظر با موفقیت برای @{username} ثبت شد")
                                    else:
                                        self.logger.warning(
                                            f"❌ خطا در ارسال نظر برای @{username}")
                                else:
                                    self.logger.warning(
                                        f"❌ شناسه مدیا یافت نشد")
                            else:
                                # شانس کمتر برای تعامل با محتوای غیر فارسی
                                if random.random() < 0.3:  # 30% احتمال
                                    media_id = None
                                    if hasattr(media, 'id'):
                                        media_id = media.id
                                    elif isinstance(media, dict) and 'id' in media:
                                        media_id = media['id']
                                    elif hasattr(media, 'pk'):
                                        media_id = media.pk
                                    elif isinstance(media, dict) and 'pk' in media:
                                        media_id = media['pk']

                                    if media_id and user_id and username:
                                        comment_result = self.actions.comment_on_media(
                                            media_id, username, user_id, hashtag, update_user_profile_func)
                                        if comment_result:
                                            self.logger.info(
                                                f"✅ نظر با موفقیت برای محتوای غیرفارسی @{username} ثبت شد")

                            # استراحت بین اکشن‌ها
                            human_sleep(15, 30)  # استراحت کوتاه‌تر بین اکشن‌ها

                        except Exception as e:
                            self.logger.error(f"❌ خطا در تعامل با رسانه: {e}")
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
            media_items = []
            try:
                self.logger.info("تلاش برای دریافت تایم‌لاین با روش اول")
                if callable(self.client.get_timeline_feed):
                    feed_items = self.client.get_timeline_feed()
                    self.logger.info(
                        f"نوع feed_items با روش اول: {type(feed_items)}")

                    # پردازش دیکشنری برگشتی
                    if isinstance(feed_items, dict):
                        # لاگ کردن کلیدهای دیکشنری برای تحلیل ساختار
                        self.logger.info(
                            f"کلیدهای feed_items: {list(feed_items.keys())}")

                        # بررسی کلیدهای احتمالی که ممکن است محتوای تایم‌لاین را داشته باشند
                        if 'feed_items' in feed_items:
                            media_items = feed_items['feed_items']
                            self.logger.info(
                                f"استفاده از کلید 'feed_items' با {len(media_items)} آیتم")
                        elif 'items' in feed_items:
                            media_items = feed_items['items']
                            self.logger.info(
                                f"استفاده از کلید 'items' با {len(media_items)} آیتم")
                        elif 'medias' in feed_items:
                            media_items = feed_items['medias']
                            self.logger.info(
                                f"استفاده از کلید 'medias' با {len(media_items)} آیتم")
                        # بررسی سایر کلیدها که ممکن است محتوای رسانه‌ای داشته باشند
                        elif 'media' in feed_items:
                            media_items = feed_items['media']
                            self.logger.info(
                                f"استفاده از کلید 'media' با {len(media_items)} آیتم")
                        elif 'feed' in feed_items:
                            media_items = feed_items['feed']
                            self.logger.info(
                                f"استفاده از کلید 'feed' با {len(media_items)} آیتم")
                        else:
                            # اگر هیچ یک از کلیدهای شناخته شده پیدا نشد، سعی کنید اولین آرایه را پیدا کنید
                            for key, value in feed_items.items():
                                if isinstance(value, list) and len(value) > 0:
                                    media_items = value
                                    self.logger.info(
                                        f"استفاده از کلید '{key}' با {len(media_items)} آیتم")
                                    break

                            if not media_items:
                                self.logger.warning(
                                    "ساختار دیکشنری feed_items ناشناخته است، تبدیل به لیست خالی")
                                media_items = []
                    elif isinstance(feed_items, list):
                        media_items = feed_items
                    else:
                        self.logger.warning(
                            f"feed_items یک لیست یا دیکشنری نیست، تبدیل به لیست خالی: {type(feed_items)}")
                        media_items = []
                else:
                    self.logger.warning(
                        "get_timeline_feed یک تابع قابل فراخوانی نیست!")
                    media_items = []
            except Exception as e:
                self.logger.warning(f"خطا در دریافت تایم‌لاین با روش اول: {e}")
                media_items = []

            # بررسی نتیجه اولیه
            if not media_items:
                # روش ۲: استفاده از user_medias برای فید
                try:
                    self.logger.info("تلاش برای دریافت مدیا با روش دوم")
                    user_id = self.client.user_id
                    media_items = self.client.user_medias(
                        user_id, 20)  # دریافت 20 پست اخیر کاربر
                    self.logger.info(
                        f"تعداد آیتم‌های یافت شده با روش دوم: {len(media_items) if isinstance(media_items, list) else 'غیر لیست'}")
                except Exception as e:
                    self.logger.warning(f"خطا در دریافت مدیا با روش دوم: {e}")
                    media_items = []

            # بررسی نتیجه دوم
            if not media_items:
                # روش ۳: استفاده از hashtag_medias_recent برای دریافت پست‌های اخیر یک هشتگ عمومی
                try:
                    self.logger.info(
                        "تلاش برای دریافت پست‌های هشتگ با روش سوم")
                    from app.config import PERSIAN_HASHTAGS

                    # انتخاب یک هشتگ تصادفی
                    hashtag = random.choice(PERSIAN_HASHTAGS)
                    self.logger.info(
                        f"استفاده از هشتگ {hashtag} برای جایگزینی تایم‌لاین")

                    media_items = self.client.hashtag_medias_recent(
                        hashtag, 10)
                    self.logger.info(
                        f"تعداد آیتم‌های یافت شده با روش سوم: {len(media_items) if isinstance(media_items, list) else 'غیر لیست'}")
                except Exception as e:
                    self.logger.warning(
                        f"خطا در دریافت پست‌های هشتگ با روش سوم: {e}")
                    media_items = []

            # اطمینان از اینکه media_items یک لیست است
            if not isinstance(media_items, list):
                self.logger.warning(
                    f"media_items یک لیست نیست، تبدیل به لیست خالی: {type(media_items)}")
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

                        # این بخش تغییر کرده است - رفع خطای slice
                        caption_text = ""
                        if caption:
                            # تبدیل caption به رشته قبل از استفاده از slice
                            if isinstance(caption, str):
                                caption_text = caption[:50]
                            elif isinstance(caption, dict):
                                # اگر caption یک دیکشنری است
                                caption_text = str(caption)[:50]
                            else:
                                caption_text = str(caption)[:50]

                        self.logger.debug(f"کپشن پست: {caption_text}")

                        if caption:
                            if isinstance(caption, str):
                                has_persian = is_persian_content(caption)
                            else:
                                # اگر caption یک رشته نیست، به رشته تبدیل می‌کنیم
                                has_persian = is_persian_content(str(caption))

                        # اولویت دادن به محتوای فارسی
                        if has_persian:
                            self.logger.info(
                                f"✅ محتوای فارسی در تایم‌لاین یافت شد: {caption_text}")

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

    def search_posts(self, query, count=20):
        """جستجوی عمومی برای پست‌ها به جای استفاده مستقیم از هشتگ"""
        try:
            self.logger.info(f"جستجوی عمومی برای '{query}'")

            # استفاده از متد جستجوی عمومی به جای هشتگ مستقیم
            posts = []

            # روش 1: تلاش با استفاده از search() اگر این متد وجود داشته باشد
            if hasattr(self.client, 'search'):
                try:
                    result = self.client.search(query)

                    # بررسی ساختار نتایج برای استخراج پست‌ها
                    if isinstance(result, dict):
                        # جستجوی پست‌ها در ساختار نتایج
                        if 'hashtags' in result and result['hashtags']:
                            # محدود به 3 هشتگ اول
                            for hashtag in result['hashtags'][:3]:
                                try:
                                    # دریافت پست‌های مرتبط با این هشتگ
                                    if hasattr(self.client, 'hashtag_medias_top'):
                                        tag_posts = self.client.hashtag_medias_top(
                                            hashtag.name, count//3)
                                        posts.extend(tag_posts)
                                    elif hasattr(self.client, 'hashtag_medias_recent'):
                                        tag_posts = self.client.hashtag_medias_recent(
                                            hashtag.name, count//3)
                                        posts.extend(tag_posts)
                                except Exception as e:
                                    self.logger.warning(
                                        f"خطا در دریافت پست‌های هشتگ {hashtag.name}: {e}")

                        if 'users' in result and result['users']:
                            for user in result['users'][:3]:  # محدود به 3 کاربر
                                try:
                                    # دریافت چند پست از هر کاربر
                                    if hasattr(self.client, 'user_medias'):
                                        user_posts = self.client.user_medias(
                                            user.pk, count//3)
                                        posts.extend(user_posts)
                                except Exception as e:
                                    self.logger.warning(
                                        f"خطا در دریافت پست‌های کاربر {user.username}: {e}")

                    # اگر result یک لیست است، ممکن است مستقیماً پست‌ها باشد
                    elif isinstance(result, list):
                        posts = result
                except Exception as search_error:
                    self.logger.warning(
                        f"خطا در روش اول جستجو: {search_error}")

            # روش 2: تلاش با استفاده از fbsearch_places() اگر این متد وجود داشته باشد
            if len(posts) < count and hasattr(self.client, 'fbsearch_places'):
                try:
                    places = self.client.fbsearch_places(query)
                    if places:
                        for place in places[:2]:  # محدود به 2 مکان
                            try:
                                if hasattr(self.client, 'location_medias_recent'):
                                    place_posts = self.client.location_medias_recent(
                                        place.pk, count//2)
                                    posts.extend(place_posts)
                            except Exception as place_error:
                                self.logger.warning(
                                    f"خطا در دریافت پست‌های مکان {place.name}: {place_error}")
                except Exception as fbsearch_error:
                    self.logger.warning(
                        f"خطا در جستجوی مکان: {fbsearch_error}")

            # روش 3: تلاش برای استفاده از search_users() اگر این متد وجود داشته باشد
            if len(posts) < count and hasattr(self.client, 'search_users'):
                try:
                    users = self.client.search_users(query)
                    if users:
                        for user in users[:3]:  # محدود به 3 کاربر
                            try:
                                if hasattr(self.client, 'user_medias'):
                                    user_posts = self.client.user_medias(
                                        user.pk, count//3)
                                    posts.extend(user_posts)
                            except Exception as user_error:
                                self.logger.warning(
                                    f"خطا در دریافت پست‌های کاربر {user.username}: {user_error}")
                except Exception as search_users_error:
                    self.logger.warning(
                        f"خطا در جستجوی کاربران: {search_users_error}")

            # روش 4: تلاش با استفاده از search_tags() اگر این متد وجود داشته باشد
            if len(posts) < count and hasattr(self.client, 'search_tags'):
                try:
                    tags = self.client.search_tags(query)
                    if tags:
                        for tag in tags[:3]:  # محدود به 3 هشتگ
                            try:
                                if hasattr(self.client, 'hashtag_medias_top'):
                                    tag_posts = self.client.hashtag_medias_top(
                                        tag.name, count//3)
                                    posts.extend(tag_posts)
                                elif hasattr(self.client, 'hashtag_medias_recent'):
                                    tag_posts = self.client.hashtag_medias_recent(
                                        tag.name, count//3)
                                    posts.extend(tag_posts)
                            except Exception as tag_error:
                                self.logger.warning(
                                    f"خطا در دریافت پست‌های هشتگ {tag.name}: {tag_error}")
                except Exception as search_tags_error:
                    self.logger.warning(
                        f"خطا در جستجوی هشتگ‌ها: {search_tags_error}")

            # روش 5: به صورت پشتیبان از feed_timeline استفاده می‌کنیم
            if len(posts) < count and hasattr(self.client, 'get_timeline_feed'):
                try:
                    timeline = self.client.get_timeline_feed()

                    # استخراج پست‌ها از timeline
                    timeline_posts = []
                    if isinstance(timeline, dict):
                        # بررسی ساختارهای مختلف خروجی
                        if 'feed_items' in timeline:
                            timeline_posts = timeline['feed_items']
                        elif 'items' in timeline:
                            timeline_posts = timeline['items']
                        elif 'medias' in timeline:
                            timeline_posts = timeline['medias']
                    elif isinstance(timeline, list):
                        timeline_posts = timeline

                    # اضافه کردن پست‌های تایم‌لاین
                    posts.extend(timeline_posts[:count//2])
                except Exception as timeline_error:
                    self.logger.warning(
                        f"خطا در دریافت تایم‌لاین: {timeline_error}")

            # حذف پست‌های تکراری
            unique_posts = []
            seen_ids = set()

            for post in posts:
                post_id = None

                # استخراج شناسه پست از ساختارهای مختلف
                if hasattr(post, 'id'):
                    post_id = post.id
                elif isinstance(post, dict) and 'id' in post:
                    post_id = post['id']
                elif hasattr(post, 'pk'):
                    post_id = post.pk
                elif isinstance(post, dict) and 'pk' in post:
                    post_id = post['pk']

                # اگر شناسه معتبر است و تکراری نیست، اضافه کن
                if post_id and post_id not in seen_ids:
                    seen_ids.add(post_id)
                    unique_posts.append(post)

                    # اگر به تعداد کافی رسیدیم، خارج شو
                    if len(unique_posts) >= count:
                        break

            self.logger.info(
                f"تعداد {len(unique_posts)} پست یافت شد با جستجوی '{query}'")
            return unique_posts

        except Exception as e:
            self.logger.error(f"خطا در جستجوی عمومی: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def find_alternative_content(self, keywords, count=5):
        """یافتن محتوا با روش‌های جایگزین وقتی جستجوی هشتگ با خطا مواجه می‌شود"""
        try:
            self.logger.info(
                f"تلاش برای یافتن محتوای جایگزین با کلیدواژه‌های: {keywords}")
            all_medias = []

            # روش 1: استفاده از لیست فالوئینگ‌ها
            try:
                from app.database.models import get_collection_name

                # اطمینان از دسترسی به دیتابیس
                if self.db is None:
                    self.logger.warning(
                        "دیتابیس در دسترس نیست، سعی می‌کنیم به روش دیگری ادامه دهیم")
                else:
                    users_collection = self.db[get_collection_name("users")]

                    # یافتن کاربرانی که دنبال می‌کنیم
                    user_docs = users_collection.find(
                        {"is_following": True}).limit(10)

                    for user in user_docs:
                        user_id = user.get("user_id")
                        if user_id:
                            try:
                                if hasattr(self.client, 'user_medias'):
                                    user_medias = self.client.user_medias(
                                        user_id, 5)
                                    all_medias.extend(user_medias)
                                    self.logger.info(
                                        f"پست‌های کاربر {user.get('username')} دریافت شد")
                            except Exception as user_error:
                                self.logger.warning(
                                    f"خطا در دریافت پست‌های کاربر {user.get('username')}: {user_error}")
            except Exception as e:
                self.logger.warning(f"خطا در روش اول جایگزین: {e}")

            # روش 2: استفاده از جستجوی عمومی
            if len(all_medias) < count:
                for keyword in keywords:
                    try:
                        if hasattr(self.client, 'search'):
                            result = self.client.search(keyword)

                            # استخراج پست‌ها از نتایج جستجو
                            if isinstance(result, dict):
                                if 'users' in result and result['users']:
                                    for user in result['users'][:3]:  # محدود به 3 کاربر
                                        try:
                                            if hasattr(self.client, 'user_medias'):
                                                user_posts = self.client.user_medias(
                                                    user.pk, 3)
                                                all_medias.extend(user_posts)
                                        except Exception as user_error:
                                            pass

                            self.logger.info(
                                f"پست‌های کلیدواژه '{keyword}' دریافت شد")
                    except Exception as search_error:
                        self.logger.warning(
                            f"خطا در جستجوی کلیدواژه {keyword}: {search_error}")

            # روش 3: تلاش برای دریافت پست‌های اکسپلور
            if len(all_medias) < count:
                try:
                    # استفاده از متد explore اگر موجود باشد
                    if hasattr(self.client, 'explore_feed'):
                        explore_posts = self.client.explore_feed()

                        # پردازش نتایج با توجه به ساختار داده
                        if isinstance(explore_posts, list):
                            all_medias.extend(explore_posts)
                            self.logger.info(
                                f"{len(explore_posts)} پست از اکسپلور دریافت شد (لیست)")
                        elif isinstance(explore_posts, dict):
                            # بررسی ساختارهای مختلف دیکشنری
                            if 'items' in explore_posts:
                                all_medias.extend(explore_posts['items'])
                                self.logger.info(
                                    f"{len(explore_posts['items'])} پست از اکسپلور دریافت شد (items)")
                            elif 'medias' in explore_posts:
                                all_medias.extend(explore_posts['medias'])
                                self.logger.info(
                                    f"{len(explore_posts['medias'])} پست از اکسپلور دریافت شد (medias)")
                            elif 'sections' in explore_posts:
                                for section in explore_posts['sections']:
                                    if 'layout_content' in section and 'medias' in section['layout_content']:
                                        all_medias.extend(
                                            section['layout_content']['medias'])
                                self.logger.info(
                                    f"پست‌های اکسپلور از بخش sections دریافت شد")
                            else:
                                # جستجوی آرایه‌ها در دیکشنری
                                for key, value in explore_posts.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        all_medias.extend(value)
                                        self.logger.info(
                                            f"پست‌های اکسپلور از کلید {key} دریافت شد")
                                        break
                except Exception as explore_error:
                    self.logger.warning(
                        f"خطا در دریافت پست‌های اکسپلور: {explore_error}")

            # روش 4: استفاده از تایم‌لاین
            if len(all_medias) < count:
                try:
                    if hasattr(self.client, 'get_timeline_feed'):
                        timeline_feed = self.client.get_timeline_feed()

                        # پردازش نتایج با توجه به ساختار داده
                        if isinstance(timeline_feed, list):
                            all_medias.extend(timeline_feed)
                            self.logger.info(
                                f"{len(timeline_feed)} پست از تایم‌لاین دریافت شد (لیست)")
                        elif isinstance(timeline_feed, dict):
                            # بررسی ساختارهای مختلف دیکشنری
                            if 'feed_items' in timeline_feed:
                                all_medias.extend(timeline_feed['feed_items'])
                                self.logger.info(
                                    f"{len(timeline_feed['feed_items'])} پست از تایم‌لاین دریافت شد (feed_items)")
                            elif 'items' in timeline_feed:
                                all_medias.extend(timeline_feed['items'])
                                self.logger.info(
                                    f"{len(timeline_feed['items'])} پست از تایم‌لاین دریافت شد (items)")
                            elif 'medias' in timeline_feed:
                                all_medias.extend(timeline_feed['medias'])
                                self.logger.info(
                                    f"{len(timeline_feed['medias'])} پست از تایم‌لاین دریافت شد (medias)")
                            else:
                                # جستجوی آرایه‌ها در دیکشنری
                                for key, value in timeline_feed.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        all_medias.extend(value)
                                        self.logger.info(
                                            f"پست‌های تایم‌لاین از کلید {key} دریافت شد")
                                        break
                except Exception as timeline_error:
                    self.logger.warning(
                        f"خطا در دریافت پست‌های تایم‌لاین: {timeline_error}")

            # روش 5: استفاده از پست‌های کاربران محبوب
            if len(all_medias) < count:
                try:
                    # لیستی از کاربران محبوب فارسی زبان (به عنوان پشتیبان)
                    popular_users = ["tehran_pictures", "iran.photographers",
                                     "persianfoodie", "iraniantraveller", "persianpoets"]

                    for username in popular_users:
                        try:
                            # دریافت اطلاعات کاربر
                            if hasattr(self.client, 'user_info_by_username'):
                                user_info = self.client.user_info_by_username(
                                    username)
                                if user_info and hasattr(user_info, 'pk'):
                                    # دریافت پست‌های کاربر
                                    if hasattr(self.client, 'user_medias'):
                                        user_posts = self.client.user_medias(
                                            user_info.pk, 3)
                                        all_medias.extend(user_posts)
                                        self.logger.info(
                                            f"پست‌های کاربر محبوب {username} دریافت شد")
                        except Exception as popular_error:
                            self.logger.warning(
                                f"خطا در دریافت پست‌های کاربر محبوب {username}: {popular_error}")
                            continue
                except Exception as e:
                    self.logger.warning(f"خطا در روش کاربران محبوب: {e}")

            # محدود کردن تعداد نتایج و حذف موارد تکراری
            unique_media_ids = set()
            unique_medias = []

            for media in all_medias:
                try:
                    # استخراج شناسه مدیا
                    media_id = None

                    if hasattr(media, 'id'):
                        media_id = media.id
                    elif isinstance(media, dict) and 'id' in media:
                        media_id = media['id']
                    elif hasattr(media, 'pk'):
                        media_id = media.pk
                    elif isinstance(media, dict) and 'pk' in media:
                        media_id = media['pk']
                    elif isinstance(media, dict) and 'media_id' in media:
                        media_id = media['media_id']

                    # اگر یک شناسه معتبر داریم و قبلاً آن را ندیده‌ایم
                    if media_id and media_id not in unique_media_ids:
                        unique_media_ids.add(media_id)
                        unique_medias.append(media)

                        # اگر به تعداد مورد نیاز رسیدیم، خارج شویم
                        if len(unique_medias) >= count:
                            break
                except Exception as process_error:
                    self.logger.warning(f"خطا در پردازش مدیا: {process_error}")
                    continue

            self.logger.info(f"تعداد {len(unique_medias)} پست جایگزین یافت شد")
            return unique_medias

        except Exception as e:
            self.logger.error(f"خطا در یافتن محتوای جایگزین: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []
