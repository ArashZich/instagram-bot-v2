import random
import re  # این خط رو اضافه کن
from typing import List, Optional
from datetime import datetime
from loguru import logger
import json
import traceback


from app.database.models import UserInteraction, InteractionType
from app.bot.utils import human_sleep, should_perform_action, humanize_text, setup_logger
from app.bot.utils import get_random_comment, get_random_dm, get_random_reaction
from app.config import COMMENT_PROBABILITY, REACTION_PROBABILITY, DM_PROBABILITY
from app.bot.content_analyzer import ContentAnalyzer


class InstagramActions:
    def __init__(self, client, db, session_id):
        self.client = client
        self.db = db
        self.session_id = session_id
        self.logger = setup_logger()
        # اضافه کردن آنالایزر محتوا
        self.content_analyzer = ContentAnalyzer()

    def _record_interaction(self, interaction: UserInteraction, update_user_profile_func):
        """ثبت تعامل کاربر در دیتابیس"""
        from app.database.models import get_collection_name

        try:
            # تبدیل به دیکشنری برای ذخیره
            interaction_dict = interaction.to_dict()

            # Sanitize any complex objects
            def sanitize_dict(d):
                result = {}
                for k, v in d.items():
                    if isinstance(v, dict):
                        result[k] = sanitize_dict(v)
                    elif isinstance(v, list):
                        # پردازش لیست‌ها
                        result[k] = [sanitize_dict(item) if isinstance(item, dict) else str(
                            item) if hasattr(item, '__dict__') else item for item in v]
                    else:
                        result[k] = str(v) if hasattr(v, '__dict__') else v
                return result

            interaction_dict = sanitize_dict(interaction_dict)

            # اضافه کردن اطلاعات تکمیلی
            interaction_dict["session_id"] = self.session_id

            # بررسی نام کالکشن صحیح
            collection_name = get_collection_name("interactions")

            # اطمینان از اتصال به دیتابیس
            if not self.db:
                self.logger.error("❌ خطا: اتصال به دیتابیس برقرار نیست!")
                from app.database.connection import get_database
                self.db = get_database()
                if not self.db:
                    self.logger.error("❌ خطا: نمی‌توان به دیتابیس متصل شد!")
                    return False

            self.logger.info(f"ذخیره تعامل در کالکشن: {collection_name}")
            self.logger.debug(f"داده تعامل: {interaction_dict}")

            # ثبت در دیتابیس با مدیریت خطا
            try:
                result = self.db[collection_name].insert_one(interaction_dict)
                self.logger.info(f"تعامل با ID: {result.inserted_id} ثبت شد.")
            except Exception as insert_error:
                self.logger.error(f"❌ خطا در درج تعامل: {insert_error}")
                import traceback
                self.logger.error(f"جزئیات خطا: {traceback.format_exc()}")
                return False

            # لاگ کردن نتیجه با شناسه
            self.logger.info(
                f"تعامل {interaction.interaction_type} با کاربر {interaction.username} ثبت شد.")

            # اطمینان از وجود تابع بروزرسانی
            if update_user_profile_func is None:
                self.logger.warning(
                    "تابع بروزرسانی پروفایل کاربر مشخص نشده است!")
                return True

            # بروزرسانی پروفایل کاربر
            try:
                update_user_profile_func(
                    user_id=interaction.user_id,
                    username=interaction.username,
                    interaction_type=interaction.interaction_type
                )
                self.logger.info(
                    f"پروفایل کاربر {interaction.username} بروزرسانی شد.")
            except Exception as profile_error:
                self.logger.error(
                    f"خطا در بروزرسانی پروفایل کاربر: {profile_error}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                # ادامه اجرا حتی در صورت خطا در بروزرسانی پروفایل

            # بررسی ذخیره موفق با بازیابی داده
            try:
                saved_interaction = self.db[collection_name].find_one(
                    {"_id": result.inserted_id})
                if saved_interaction:
                    self.logger.info(
                        f"تعامل با موفقیت ذخیره و بازیابی شد: {saved_interaction.get('interaction_type')}")
                else:
                    self.logger.warning(f"تعامل ذخیره شد اما بازیابی نشد!")
            except Exception as verify_error:
                self.logger.error(f"خطا در تأیید ذخیره تعامل: {verify_error}")

            return True

        except Exception as e:
            self.logger.error(f"❌ خطا در ثبت تعامل: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def follow_user(self, user_id: str, username: str, update_user_profile_func):
        """دنبال کردن یک کاربر و ثبت تعامل"""
        try:
            self.client.user_follow(user_id)
            human_sleep(3, 8)  # تأخیر طبیعی‌تر

            # ثبت تعامل
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.FOLLOW,
                timestamp=datetime.now()
            )
            self._record_interaction(interaction, update_user_profile_func)

            self.logger.info(f"Followed user: {username}")
            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.warning(
                    f"چالش امنیتی هنگام دنبال کردن کاربر {username}")
                return False

            self.logger.error(f"Failed to follow user {username}: {e}")
            return False

    def unfollow_user(self, user_id: str, username: str, update_user_profile_func):
        """لغو دنبال کردن یک کاربر و ثبت تعامل"""
        try:
            self.client.user_unfollow(user_id)
            human_sleep(3, 8)  # تأخیر طبیعی‌تر

            # ثبت تعامل
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.UNFOLLOW,
                timestamp=datetime.now()
            )
            self._record_interaction(interaction, update_user_profile_func)

            self.logger.info(f"Unfollowed user: {username}")
            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.warning(
                    f"چالش امنیتی هنگام لغو دنبال کردن کاربر {username}")
                return False

            self.logger.error(f"Failed to unfollow user {username}: {e}")
            return False

    def comment_on_media(self, media_id: str, username: str, user_id: str, topic: str = None, update_user_profile_func=None):
        """نظر دادن روی یک پست و ثبت تعامل"""
        if not should_perform_action(COMMENT_PROBABILITY):
            return False

        try:
            # دریافت اطلاعات پست
            try:
                media_info = self.client.media_info(media_id)

                # استخراج کپشن
                caption = ""
                if hasattr(media_info, "caption_text") and media_info.caption_text:
                    caption = media_info.caption_text
                elif hasattr(media_info, "caption") and media_info.caption:
                    caption = media_info.caption
                elif isinstance(media_info, dict) and "caption" in media_info:
                    caption = media_info["caption"]

                # استخراج هشتگ‌ها
                hashtags = []
                if caption:
                    hashtags = re.findall(r'#(\w+)', caption)

                self.logger.debug(f"Caption retrieved: {caption[:100]}...")
                if hashtags:
                    self.logger.debug(f"Hashtags: {hashtags}")

            except Exception as e:
                self.logger.warning(f"خطا در دریافت اطلاعات پست: {e}")
                caption = ""
                hashtags = []

            # تحلیل محتوا و تشخیص موضوع
            detected_topic = self.content_analyzer.analyze(caption, hashtags)
            self.logger.info(f"Detected topic from content: {detected_topic}")

            # ترکیب موضوع هشتگ و موضوع تشخیص داده شده
            if topic and detected_topic != "general":
                final_topic = detected_topic  # اولویت با موضوع تشخیص داده شده
            elif topic:
                final_topic = topic
            else:
                final_topic = detected_topic

            # دریافت متن کامنت و انسانی‌سازی آن
            comment_text = humanize_text(get_random_comment(final_topic))

            # افزودن کامنت
            self.client.media_comment(media_id, comment_text)
            human_sleep(5, 15)  # تأخیر طبیعی‌تر و طولانی‌تر

            # ثبت تعامل
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.COMMENT,
                timestamp=datetime.now(),
                content=comment_text,
                media_id=media_id,
                metadata={
                    "topic": final_topic,
                    "is_persian": True,
                    "detected_from_content": detected_topic != "general",
                    "hashtags": hashtags
                }
            )
            self._record_interaction(interaction, update_user_profile_func)

            self.logger.info(
                f"Commented on media {media_id} from {username} with topic {final_topic}: {comment_text}")
            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.warning(
                    f"چالش امنیتی هنگام کامنت گذاشتن برای کاربر {username}")
                return False

            self.logger.error(f"Failed to comment on media {media_id}: {e}")
            return False

    def react_to_story(self, story_id: str, username: str, user_id: str, update_user_profile_func):
        """واکنش به استوری و ثبت تعامل"""
        if not should_perform_action(REACTION_PROBABILITY):
            return False

        try:
            # دریافت ایموجی واکنش
            reaction = get_random_reaction()
            self.logger.info(
                f"تلاش برای ارسال واکنش {reaction} به استوری {story_id} از کاربر {username}")

            # روش اول: تلاش برای استفاده از story_send_reaction اگر موجود باشد
            reaction_sent = False

            if hasattr(self.client, 'story_send_reaction'):
                try:
                    self.logger.info("استفاده از روش story_send_reaction")
                    self.client.story_send_reaction(story_id, reaction)
                    reaction_sent = True
                    self.logger.info(
                        f"✅ واکنش {reaction} به استوری {story_id} از {username} ارسال شد (روش 1)")
                except Exception as e:
                    self.logger.warning(f"خطا در روش story_send_reaction: {e}")
                    # ادامه با روش‌های بعدی

            # روش دوم: استفاده از story_seen
            if not reaction_sent and hasattr(self.client, 'story_seen'):
                try:
                    self.logger.info("استفاده از روش story_seen")
                    result = self.client.story_seen([story_id])
                    self.logger.info(f"نتیجه story_seen: {result}")

                    # بعد از دیدن استوری، ارسال واکنش از طریق direct
                    if hasattr(self.client, 'direct_send'):
                        self.client.direct_send(
                            reaction, [user_id], thread_ids=[story_id])
                        reaction_sent = True
                        self.logger.info(
                            f"✅ واکنش {reaction} به استوری {story_id} از {username} ارسال شد (روش 2)")
                except Exception as e:
                    self.logger.warning(
                        f"خطا در روش story_seen + direct_send: {e}")

            # روش سوم: استفاده از direct_answer
            if not reaction_sent and hasattr(self.client, 'direct_answer'):
                try:
                    self.logger.info("استفاده از روش direct_answer")
                    self.client.direct_answer(story_id, reaction)
                    reaction_sent = True
                    self.logger.info(
                        f"✅ واکنش {reaction} به استوری {story_id} از {username} ارسال شد (روش 3)")
                except Exception as e:
                    self.logger.warning(f"خطا در روش direct_answer: {e}")

            # روش چهارم: استفاده از direct_send به تنهایی
            if not reaction_sent and hasattr(self.client, 'direct_send'):
                try:
                    self.logger.info("استفاده از روش direct_send")
                    # ارسال پیام مستقیم به کاربر
                    message = f"واکنش به استوری: {reaction}"
                    self.client.direct_send(message, [user_id])
                    reaction_sent = True
                    self.logger.info(
                        f"✅ واکنش {reaction} به کاربر {username} ارسال شد (روش 4)")
                except Exception as e:
                    self.logger.warning(f"خطا در روش direct_send: {e}")

            # اگر هیچ روشی موفقیت‌آمیز نبود
            if not reaction_sent:
                self.logger.warning(
                    f"❌ تمام روش‌های ارسال واکنش به استوری ناموفق بودند")
                return False

            human_sleep(4, 10)  # تأخیر طبیعی‌تر

            # ثبت تعامل فقط در صورت موفقیت ارسال واکنش
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.STORY_REACTION,
                timestamp=datetime.now(),
                content=reaction,
                media_id=story_id
            )
            record_result = self._record_interaction(
                interaction, update_user_profile_func)

            if record_result:
                self.logger.info(f"✅ تعامل واکنش به استوری در دیتابیس ثبت شد")
            else:
                self.logger.warning(
                    f"❌ خطا در ثبت تعامل واکنش به استوری در دیتابیس")

            self.logger.info(
                f"Reacted to story {story_id} from {username} with {reaction}")
            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.warning(
                    f"چالش امنیتی هنگام واکنش به استوری کاربر {username}")
                return False

            self.logger.error(f"Failed to react to story {story_id}: {e}")
            return False

    def send_direct_message(self, user_id: str, username: str, topic: str = None, update_user_profile_func=None):
        """ارسال پیام مستقیم و ثبت تعامل"""
        if not should_perform_action(DM_PROBABILITY):
            return False

        try:
            # دریافت متن پیام و انسانی‌سازی آن
            message_text = humanize_text(get_random_dm(topic))

            # ارسال پیام
            self.client.direct_send(message_text, [user_id])
            human_sleep(8, 20)  # تأخیر طولانی‌تر برای دایرکت

            # ثبت تعامل
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.DIRECT_MESSAGE,
                timestamp=datetime.now(),
                content=message_text,
                metadata={"topic": topic, "is_persian": True}
            )
            self._record_interaction(interaction, update_user_profile_func)

            self.logger.info(f"Sent DM to {username}: {message_text}")
            return True

        except Exception as e:
            if "challenge_required" in str(e).lower():
                self.logger.warning(
                    f"چالش امنیتی هنگام ارسال پیام به کاربر {username}")
                return False

            self.logger.error(f"Failed to send DM to {username}: {e}")
            return False
