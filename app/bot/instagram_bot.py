import time
import random
import uuid
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError, ClientLoginRequired
import pickle
from loguru import logger
from pathlib import Path
import schedule
import threading
import traceback

from app.config import (
    INSTAGRAM_USERNAME,
    INSTAGRAM_PASSWORD,
    DAILY_INTERACTION_LIMIT,
    COMMENT_PROBABILITY,
    REACTION_PROBABILITY,
    DM_PROBABILITY,
    get_random_interval,
    get_random_session_duration,
    get_random_break_duration
)
from app.database.connection import get_database
from app.database.models import (
    UserInteraction,
    InteractionType,
    UserProfile,
    BotSession,
    get_collection_name
)
from app.bot.utils import (
    setup_logger,
    human_sleep,
    should_perform_action,
    generate_session_id,
    get_random_comment,
    get_random_dm,
    get_random_reaction,
    humanize_text
)


class InstagramBot:
    def __init__(self):
        self.client = Client()
        self.username = INSTAGRAM_USERNAME
        self.password = INSTAGRAM_PASSWORD
        self.db = get_database()
        self.logger = setup_logger()
        self.session_id = generate_session_id()
        self.is_running = False
        self.daily_interactions = 0
        self.last_check_follower_time = datetime.now()
        self.session_start_time = datetime.now()
        self.session_end_time = self.session_start_time + \
            timedelta(seconds=get_random_session_duration())
        # اضافه کردن فیلد logged_in
        self.logged_in = False
        self.last_error = None
        self.last_operation = "راه‌اندازی"

        # Create collections if they don't exist
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize database collections if they don't exist"""
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
                self.logger.info(f"Created collection: {collection}")

    def login(self) -> bool:
        """لاگین ساده به اینستاگرام"""
        try:
            if self.logged_in:
                return True

            self.logger.info(f"تلاش برای لاگین با کاربر {self.username}")
            self.last_operation = "لاگین به اینستاگرام"

            # تست اتصال به اینترنت
            try:
                import requests
                self.logger.info("تست اتصال به اینترنت...")
                response = requests.get("https://www.google.com", timeout=10)
                self.logger.info(
                    f"✅ اتصال به اینترنت موفق: {response.status_code}")
            except Exception as ne:
                self.logger.error(f"❌ مشکل در اتصال به اینترنت: {str(ne)}")

            # تنظیم پارامترهای کلاینت و لاگین
            self.client.delay_range = [2, 5]
            self.client.request_timeout = 60

            self.logger.info("در حال اجرای لاگین...")
            login_result = self.client.login(self.username, self.password)
            self.logger.info(f"نتیجه لاگین: {login_result}")

            self.logged_in = True
            self.logger.info("✅ ورود موفقیت‌آمیز به اینستاگرام")
            return True

        except Exception as e:
            self.logged_in = False
            self.logger.error(f"❌ خطا در لاگین: {str(e)}")
            self.last_error = str(e)
            import traceback
            traceback.print_exc()
            return False

    def _record_session_start(self):
        """Record session start in database"""
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

    def _record_session_end(self):
        """Record session end in database"""
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

    def _record_interaction(self, interaction: UserInteraction):
        """Record user interaction in database"""
        self.db[get_collection_name("interactions")].insert_one(
            interaction.to_dict())
        self.daily_interactions += 1

        # Update user profile
        self._update_user_profile(
            user_id=interaction.user_id,
            username=interaction.username,
            interaction_type=interaction.interaction_type
        )

        self.logger.info(
            f"Recorded {interaction.interaction_type} interaction with user {interaction.username}")

    def _update_user_profile(self, user_id: str, username: str, interaction_type: str):
        """Update or create user profile in database"""
        # Get existing user profile
        user_data = self.db[get_collection_name("users")].find_one({
            "user_id": user_id})

        if user_data:
            # Update existing profile
            self.db[get_collection_name("users")].update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "last_interaction": datetime.now(),
                    },
                    "$inc": {
                        "interaction_count": 1
                    },
                    "$addToSet": {
                        "metadata.interaction_types": interaction_type
                    }
                }
            )
        else:
            # Create new user profile
            user_info = None
            try:
                user_info = self.client.user_info_by_username(username)
            except Exception as e:
                self.logger.warning(
                    f"Could not fetch user info for {username}: {e}")

            user_profile = UserProfile(
                user_id=user_id,
                username=username,
                full_name=user_info.full_name if user_info else None,
                is_following=False,  # Will be updated during follower check
                is_follower=False,   # Will be updated during follower check
                interaction_count=1,
                last_interaction=datetime.now(),
                first_seen=datetime.now(),
                metadata={
                    "interaction_types": [interaction_type],
                    "user_info": user_info.dict() if user_info else {}
                }
            )

            self.db[get_collection_name("users")].insert_one(
                user_profile.to_dict())

    def check_and_update_followers(self):
        """Check for new followers and update database"""
        if (datetime.now() - self.last_check_follower_time).total_seconds() < 3600:
            # Don't check more than once per hour
            return

        self.logger.info("Checking followers and following")

        try:
            # Get current followers and following
            followers = set(self.client.user_followers(
                self.client.user_id).keys())
            following = set(self.client.user_following(
                self.client.user_id).keys())

            # Update database
            for user_id in followers.union(following):
                is_follower = user_id in followers
                is_following = user_id in following

                # Try to get username
                username = None
                try:
                    user_info = self.client.user_info(user_id)
                    username = user_info.username
                except Exception as e:
                    self.logger.warning(
                        f"Could not fetch username for user {user_id}: {e}")

                if not username:
                    continue

                # Update database
                existing_user = self.db[get_collection_name(
                    "users")].find_one({"user_id": user_id})

                if existing_user:
                    # Update existing user
                    self.db[get_collection_name("users")].update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "is_follower": is_follower,
                            "is_following": is_following
                        }}
                    )

                    # If user is no longer following us but we are following them, unfollow
                    if not is_follower and is_following and existing_user.get("is_follower", False):
                        self.logger.info(
                            f"User {username} unfollowed us, unfollowing them")
                        self.unfollow_user(user_id, username)

                    # If user has followed us and we're not following them, follow back
                    elif is_follower and not is_following and not existing_user.get("is_follower", False):
                        self.logger.info(
                            f"New follower {username}, following back")
                        self.follow_user(user_id, username)
                else:
                    # Create new user profile
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

                    # If new follower, follow back
                    if is_follower and not is_following:
                        self.logger.info(
                            f"New follower {username}, following back")
                        self.follow_user(user_id, username)

            self.last_check_follower_time = datetime.now()

        except Exception as e:
            self.logger.error(f"Error checking followers: {e}")
            traceback.print_exc()

    def follow_user(self, user_id: str, username: str):
        """Follow a user and record interaction"""
        try:
            self.client.user_follow(user_id)
            human_sleep(2, 5)

            # Record interaction
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.FOLLOW,
                timestamp=datetime.now()
            )
            self._record_interaction(interaction)

            self.logger.info(f"Followed user: {username}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to follow user {username}: {e}")
            return False

    def unfollow_user(self, user_id: str, username: str):
        """Unfollow a user and record interaction"""
        try:
            self.client.user_unfollow(user_id)
            human_sleep(2, 5)

            # Record interaction
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.UNFOLLOW,
                timestamp=datetime.now()
            )
            self._record_interaction(interaction)

            self.logger.info(f"Unfollowed user: {username}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to unfollow user {username}: {e}")
            return False

    def comment_on_media(self, media_id: str, username: str, user_id: str, topic: str = None):
        """Comment on a media post and record interaction"""
        if not should_perform_action(COMMENT_PROBABILITY):
            return False

        try:
            # Get comment text and humanize it
            comment_text = humanize_text(get_random_comment(topic))

            # Add comment
            self.client.media_comment(media_id, comment_text)
            human_sleep(3, 8)

            # Record interaction
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.COMMENT,
                timestamp=datetime.now(),
                content=comment_text,
                media_id=media_id
            )
            self._record_interaction(interaction)

            self.logger.info(
                f"Commented on media {media_id} from {username}: {comment_text}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to comment on media {media_id}: {e}")
            return False

    def react_to_story(self, story_id: str, username: str, user_id: str):
        """React to a story and record interaction"""
        if not should_perform_action(REACTION_PROBABILITY):
            return False

        try:
            # Get reaction emoji
            reaction = get_random_reaction()

            # React to story
            self.client.story_send_reaction(story_id, reaction)
            human_sleep(2, 6)

            # Record interaction
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.STORY_REACTION,
                timestamp=datetime.now(),
                content=reaction,
                media_id=story_id
            )
            self._record_interaction(interaction)

            self.logger.info(
                f"Reacted to story {story_id} from {username} with {reaction}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to react to story {story_id}: {e}")
            return False

    def send_direct_message(self, user_id: str, username: str, topic: str = None):
        """Send a direct message and record interaction"""
        if not should_perform_action(DM_PROBABILITY):
            return False

        try:
            # Get message text and humanize it
            message_text = humanize_text(get_random_dm(topic))

            # Send message
            self.client.direct_send(message_text, [user_id])
            human_sleep(5, 10)

            # Record interaction
            interaction = UserInteraction(
                user_id=user_id,
                username=username,
                interaction_type=InteractionType.DIRECT_MESSAGE,
                timestamp=datetime.now(),
                content=message_text
            )
            self._record_interaction(interaction)

            self.logger.info(f"Sent DM to {username}: {message_text}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send DM to {username}: {e}")
            return False

    def explore_hashtags(self, hashtags: List[str], count: int = 5):
        """Explore posts with specified hashtags and interact with them"""
        for hashtag in hashtags:
            self.logger.info(f"🔍 Exploring hashtag: #{hashtag}")

            try:
                # Get medias by hashtag
                self.logger.info(f"Fetching recent posts for #{hashtag}")
                medias = self.client.hashtag_medias_recent(hashtag, count)
                self.logger.info(f"Found {len(medias)} posts for #{hashtag}")

                for i, media in enumerate(medias):
                    # Check if we've reached interaction limit
                    if self.daily_interactions >= DAILY_INTERACTION_LIMIT:
                        self.logger.info(
                            "Daily interaction limit reached, stopping")
                        return

                    try:
                        user_id = media.user.pk
                        username = media.user.username

                        self.logger.info(
                            f"Post {i+1}/{len(medias)}: Interacting with @{username}'s post")

                        # Comment on post
                        comment_result = self.comment_on_media(
                            media.id, username, user_id, hashtag)

                        if comment_result:
                            self.logger.info(
                                f"✅ Successfully commented on @{username}'s post")

                        # Sleep between actions
                        human_sleep()

                    except Exception as e:
                        self.logger.error(
                            f"❌ Error interacting with media {media.id}: {e}")

            except Exception as e:
                self.logger.error(f"❌ Error exploring hashtag {hashtag}: {e}")

    def explore_timeline(self, count: int = 10):
        """Explore timeline posts and interact with them"""
        self.logger.info("Exploring timeline")

        try:
            # Get timeline feed
            feed_items = self.client.get_timeline_feed()

            for item in feed_items:
                # Check if we've reached interaction limit
                if self.daily_interactions >= DAILY_INTERACTION_LIMIT:
                    self.logger.info(
                        "Daily interaction limit reached, stopping")
                    return

                if not hasattr(item, 'media_or_ad'):
                    continue

                media = item.media_or_ad

                try:
                    user_id = media.user.pk
                    username = media.user.username

                    # Comment on post
                    self.comment_on_media(media.id, username, user_id)

                    # Sleep between actions
                    human_sleep()

                except Exception as e:
                    self.logger.error(
                        f"Error interacting with timeline media: {e}")

                # Limit to specified count
                count -= 1
                if count <= 0:
                    break

        except Exception as e:
            self.logger.error(f"Error exploring timeline: {e}")

    def check_stories(self, count: int = 5):
        """Check and react to stories"""
        self.logger.info("Checking stories")

        try:
            # در نسخه جدید instagrapi، get_reels_tray نیست و باید از متدهای دیگه استفاده کنیم

            # گرفتن لیست افرادی که دنبال می‌کنیم
            following = self.client.user_following(self.client.user_id)

            # انتخاب چند کاربر تصادفی
            selected_users = list(following.keys())
            random.shuffle(selected_users)
            # حداکثر 10 کاربر انتخاب می‌کنیم
            selected_users = selected_users[:min(10, len(selected_users))]

            user_count = 0
            for user_id in selected_users:
                # Check if we've reached interaction limit
                if self.daily_interactions >= DAILY_INTERACTION_LIMIT:
                    self.logger.info(
                        "Daily interaction limit reached, stopping")
                    return

                try:
                    # دریافت اطلاعات کاربر
                    user_info = self.client.user_info(user_id)
                    username = user_info.username

                    self.logger.info(f"Checking stories for user: {username}")

                    # Get user stories
                    stories = self.client.user_stories(user_id)

                    if stories:
                        self.logger.info(
                            f"Found {len(stories)} stories for {username}")

                        # انتخاب یک استوری تصادفی
                        story = random.choice(stories)

                        # واکنش به استوری
                        self.react_to_story(story.id, username, user_id)

                        # Sleep between actions
                        human_sleep()

                        # افزایش شمارنده
                        user_count += 1
                        if user_count >= count:
                            return

                except Exception as e:
                    self.logger.error(
                        f"Error checking stories for user {user_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error checking stories: {e}")

    def interact_with_followers(self, count: int = 5):
        """Interact with followers by sending DMs"""
        self.logger.info("Interacting with followers")

        try:
            # Get followers who we haven't sent a DM recently
            followers = self.db[get_collection_name("users")].find({
                "is_follower": True,
                "$or": [
                    {"last_interaction": {"$lt": datetime.now() - timedelta(days=7)}},
                    {"last_interaction": {"$exists": False}}
                ]
            }).limit(count)

            for follower in followers:
                # Check if we've reached interaction limit
                if self.daily_interactions >= DAILY_INTERACTION_LIMIT:
                    self.logger.info(
                        "Daily interaction limit reached, stopping")
                    return

                user_id = follower["user_id"]
                username = follower["username"]

                # Send DM
                self.send_direct_message(user_id, username, "appreciation")

                # Sleep between actions
                human_sleep()

        except Exception as e:
            self.logger.error(f"Error interacting with followers: {e}")

    def reset_daily_interactions(self):
        """Reset daily interaction counter"""
        self.daily_interactions = 0
        self.logger.info("Reset daily interaction counter")

    def run_session(self):
        """Run a single bot session with natural breaks"""
        # Set a login timeout
        login_start_time = datetime.now()
        login_timeout = 120  # 2 minutes timeout

        self.logger.info(f"⏱ Setting login timeout to {login_timeout} seconds")

        if not self.login():
            self.logger.error("❌ Login failed, cannot start bot")
            return

        login_duration = (datetime.now() - login_start_time).total_seconds()
        self.logger.info(f"⏱ Login process took {login_duration:.2f} seconds")

        self.is_running = True
        self.session_start_time = datetime.now()
        self.session_end_time = self.session_start_time + \
            timedelta(seconds=get_random_session_duration())

        self.logger.info(
            f"📅 Starting bot session: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')} to {self.session_end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Main bot loop
        while self.is_running and datetime.now() < self.session_end_time:
            try:
                # Check if we've reached daily interaction limit
                if self.daily_interactions >= DAILY_INTERACTION_LIMIT:
                    self.logger.info(
                        f"⚠️ Daily interaction limit reached ({self.daily_interactions}/{DAILY_INTERACTION_LIMIT}), taking a break")
                    human_sleep(1800, 3600)  # Sleep 30-60 minutes
                    continue

                # Check and update followers/following
                self.logger.info("🔄 Checking followers and following status")
                self.check_and_update_followers()

                # Choose a random action based on priorities and time of day
                action = random.choices(
                    ["explore_hashtags", "explore_timeline",
                        "check_stories", "interact_with_followers"],
                    weights=[0.4, 0.3, 0.2, 0.1],
                    k=1
                )[0]

                self.logger.info(f"🎯 Selected action: {action}")

                if action == "explore_hashtags":
                    hashtags = ["travel", "food", "photography",
                                "nature", "art", "fashion", "fitness"]
                    selected_hashtags = random.sample(hashtags, 2)
                    self.logger.info(
                        f"🔍 Exploring hashtags: {selected_hashtags}")
                    self.explore_hashtags(
                        selected_hashtags, count=random.randint(2, 5))
                elif action == "explore_timeline":
                    self.logger.info("📱 Exploring timeline")
                    self.explore_timeline(count=random.randint(3, 8))
                elif action == "check_stories":
                    self.logger.info("📊 Checking stories")
                    self.check_stories(count=random.randint(2, 5))
                elif action == "interact_with_followers":
                    self.logger.info("👥 Interacting with followers")
                    self.interact_with_followers(count=random.randint(1, 3))

                # Take a natural break between action groups
                sleep_duration = get_random_interval()
                self.logger.info(
                    f"⏱ Taking a break for {sleep_duration} seconds")
                human_sleep(sleep_duration, sleep_duration + 30)

                # Log current stats
                self.logger.info(
                    f"📊 Current stats: {self.daily_interactions}/{DAILY_INTERACTION_LIMIT} interactions today")

            except Exception as e:
                self.logger.error(f"❌ Error in bot loop: {e}")
                traceback.print_exc()
                human_sleep(300, 600)  # Sleep 5-10 minutes on error

        # End session
        self._record_session_end()
        self.is_running = False
        self.logger.info("✅ Bot session ended")

        # Schedule next session after a break
        break_duration = get_random_break_duration()
        next_session_time = datetime.now() + timedelta(seconds=break_duration)
        self.logger.info(
            f"⏭️ Next session scheduled at {next_session_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def run_continuously(self):
        """Run the bot continuously with natural sessions and breaks"""
        def _worker():
            # Schedule daily reset at midnight
            schedule.every().day.at("00:00").do(self.reset_daily_interactions)

            while True:
                try:
                    # Run scheduled tasks
                    schedule.run_pending()

                    # If not running, start a new session
                    if not self.is_running:
                        self.logger.info("🔄 Starting a new bot session...")

                        try:
                            self.run_session()
                        except Exception as e:
                            self.logger.error(f"❌ Error in session: {e}")
                            traceback.print_exc()
                            self.is_running = False
                            # Wait 5 minutes before trying again
                            time.sleep(300)

                        # After session ends, take a break before next session
                        break_duration = get_random_break_duration()
                        self.logger.info(
                            f"⏸ Taking a break for {break_duration/60:.1f} minutes")
                        human_sleep(break_duration, break_duration + 300)

                    time.sleep(1)

                except Exception as e:
                    self.logger.error(f"❌ Error in worker thread: {e}")
                    traceback.print_exc()
                    time.sleep(60)

        # Start worker thread
        worker_thread = threading.Thread(target=_worker)
        worker_thread.daemon = True
        worker_thread.start()

        self.logger.info("🤖 Bot started in continuous mode")
        return worker_thread

    def stop(self):
        """Stop the bot"""
        self.is_running = False
        self._record_session_end()
        self.logger.info("Bot stopped")
