import json
import random
import time
import sys
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from app.config import (
    TEMPLATES_DIR,
    get_random_interval,
    MIN_ACTION_INTERVAL,
    MAX_ACTION_INTERVAL
)

# Setup logging


# تنظیمات بهتر لاگینگ در app/bot/utils.py
def setup_logger():
    """Configure the logger"""
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    logger.remove()  # حذف تنظیمات پیش‌فرض

    # افزودن خروجی کنسول
    logger.add(
        sys.stderr,
        format=log_format,
        level="DEBUG",
        colorize=True
    )

    # افزودن لاگ فایل با چرخش
    logger.add(
        "logs/instagram_bot_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # چرخش روزانه در نیمه‌شب
        retention="7 days",  # نگهداری 7 روز آخر
        compression="zip",  # فشرده‌سازی فایل‌های قدیمی
        format=log_format,
        level="DEBUG",
        encoding="utf-8"
    )

    # افزودن لاگ خطاها به صورت جداگانه
    logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format=log_format,
        level="ERROR",
        encoding="utf-8"
    )

    return logger

# Load templates


def load_templates(template_name: str) -> List[Dict[str, str]]:
    """Load interaction templates from JSON files"""
    try:
        template_path = TEMPLATES_DIR / f"{template_name}.json"
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading template {template_name}: {e}")
        # Return some default templates as fallback
        if template_name == "comments":
            return [
                {"text": "این پست خیلی جالب بود! 👍", "topics": ["general"]},
                {"text": "عکس قشنگیه! 📸", "topics": ["photo"]},
                {"text": "واقعا عالی هست 👏", "topics": ["general"]}
            ]
        elif template_name == "direct_messages":
            return [
                {"text": "سلام! عکس‌های پروفایلت خیلی عالیه! 👋",
                    "topics": ["introduction"]},
                {"text": "از فعالیت‌هات تو اینستاگرام خیلی خوشم میاد 👍",
                    "topics": ["appreciation"]},
                {"text": "پست آخرت خیلی جالب بود! 😊", "topics": ["engagement"]}
            ]
        elif template_name == "reactions":
            return ["❤️", "🔥", "👏", "😍", "👌"]
        return []

# Get random comment


def get_random_comment(topic: str = None) -> str:
    """Get a random comment from comments template, optionally filtered by topic"""
    comments = load_templates("comments")

    if topic:
        filtered_comments = [
            c for c in comments if topic in c.get("topics", [])]
        if filtered_comments:
            return random.choice(filtered_comments)["text"]

    return random.choice(comments)["text"]

# Get random direct message


def get_random_dm(topic: str = None) -> str:
    """Get a random direct message from templates, optionally filtered by topic"""
    messages = load_templates("direct_messages")

    if topic:
        filtered_messages = [
            m for m in messages if topic in m.get("topics", [])]
        if filtered_messages:
            return random.choice(filtered_messages)["text"]

    return random.choice(messages)["text"]

# Get random story reaction


def get_random_reaction() -> str:
    """Get a random emoji reaction for stories"""
    reactions = load_templates("reactions")
    return random.choice(reactions)

# Add randomized sleep function with humanized behavior


def human_sleep(min_seconds: int = None, max_seconds: int = None) -> None:
    """Sleep for a randomized duration to mimic human behavior"""
    if min_seconds is None:
        min_seconds = MIN_ACTION_INTERVAL
    if max_seconds is None:
        max_seconds = MAX_ACTION_INTERVAL

    sleep_time = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
    time.sleep(sleep_time)

# Decide based on probability


def should_perform_action(probability: float) -> bool:
    """Decide whether to perform an action based on probability (0.0-1.0)"""
    return random.random() < probability

# Generate session ID


def generate_session_id() -> str:
    """Generate a unique session ID"""
    return f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

# Format datetime for MongoDB


def format_datetime(dt: datetime) -> str:
    """Format datetime for MongoDB"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

# Humanize text with typos and variations


def humanize_text(text: str, typo_probability: float = 0.05) -> str:
    """Add occasional typos or variations to text to seem more human"""
    if random.random() > 0.2:  # 20% chance to modify the text
        return text

    words = text.split()
    for i in range(len(words)):
        if random.random() < typo_probability:
            # Choose a random modification
            mod_type = random.choice(["typo", "case", "punctuation"])

            if mod_type == "typo" and len(words[i]) > 3:
                # Introduce a simple typo (character swap)
                char_pos = random.randint(1, len(words[i]) - 2)
                chars = list(words[i])
                chars[char_pos], chars[char_pos +
                                       1] = chars[char_pos + 1], chars[char_pos]
                words[i] = ''.join(chars)

            elif mod_type == "case" and len(words[i]) > 0:
                # Randomly change case of a character
                char_pos = random.randint(0, len(words[i]) - 1)
                chars = list(words[i])
                if chars[char_pos].islower():
                    chars[char_pos] = chars[char_pos].upper()
                else:
                    chars[char_pos] = chars[char_pos].lower()
                words[i] = ''.join(chars)

            elif mod_type == "punctuation" and i == len(words) - 1:
                # Add or remove punctuation
                if words[i][-1] in ['.', '!', '?']:
                    words[i] = words[i][:-1]
                else:
                    words[i] = words[i] + random.choice(['.', '!', '?'])

    return ' '.join(words)


def is_persian_content(text):
    """تشخیص محتوای فارسی"""
    if not text:
        return False

    # بررسی نوع ورودی - اگر دیکشنری یا غیر رشته است، به رشته تبدیل کنیم
    if not isinstance(text, str):
        try:
            # اگر دیکشنری است، سعی می‌کنیم مقدار متنی آن را استخراج کنیم
            if isinstance(text, dict):
                # اگر کلیدهای مرتبط با متن را دارد استفاده کنیم
                if 'text' in text:
                    text = text['text']
                elif 'caption' in text:
                    text = text['caption']
                else:
                    # تبدیل کل دیکشنری به رشته
                    text = str(text)
            else:
                # تبدیل به رشته
                text = str(text)
        except Exception as e:
            # اگر تبدیل با خطا مواجه شد، لاگ کنیم و False برگردانیم
            logger.error(f"خطا در تبدیل محتوا به رشته: {e}")
            return False

    # ادامه روند قبلی
    persian_chars = set('آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی')
    text_chars = set(text.replace(" ", ""))

    # اگر حداقل 20٪ حروف فارسی باشند
    return len(persian_chars.intersection(text_chars)) / max(len(text_chars), 1) > 0.2
