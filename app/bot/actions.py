import random
from typing import List, Optional
from datetime import datetime
from loguru import logger
import traceback


from app.database.models import UserInteraction, InteractionType
from app.bot.utils import human_sleep, should_perform_action, humanize_text, setup_logger
from app.bot.utils import get_random_comment, get_random_dm, get_random_reaction
from app.config import COMMENT_PROBABILITY, REACTION_PROBABILITY, DM_PROBABILITY


class InstagramActions:
    def __init__(self, client, db, session_id):
        self.client = client
        self.db = db
        self.session_id = session_id
        self.logger = setup_logger()

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
                    else:
                        result[k] = str(v) if hasattr(v, '__dict__') else v
                return result

            interaction_dict = sanitize_dict(interaction_dict)

            # اضافه کردن اطلاعات تکمیلی
            interaction_dict["session_id"] = self.session_id

            # ثبت در دیتابیس
            result = self.db[get_collection_name(
                "interactions")].insert_one(interaction_dict)

            # لاگ کردن نتیجه با شناسه
            self.logger.info(
                f"تعامل {interaction.interaction_type} با کاربر {interaction.username} ثبت شد. (ID: {result.inserted_id})")

            # بروزرسانی پروفایل کاربر
            update_user_profile_func(
                user_id=interaction.user_id,
                username=interaction.username,
                interaction_type=interaction.interaction_type
            )

            return True

        except Exception as e:
            self.logger.error(f"خطا در ثبت تعامل: {e}")
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
            # دریافت متن کامنت و انسانی‌سازی آن
            comment_text = humanize_text(get_random_comment(topic))

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
                metadata={"topic": topic, "is_persian": True}
            )
            self._record_interaction(interaction, update_user_profile_func)

            self.logger.info(
                f"Commented on media {media_id} from {username}: {comment_text}")
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

            # واکنش به استوری
            self.client.story_send_reaction(story_id, reaction)
            human_sleep(4, 10)  # تأخیر طبیعی‌تر

            # ثبت تعامل
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.STORY_REACTION,
                timestamp=datetime.now(),
                content=reaction,
                media_id=story_id
            )
            self._record_interaction(interaction, update_user_profile_func)

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
