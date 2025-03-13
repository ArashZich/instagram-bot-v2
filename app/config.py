import os
from dotenv import load_dotenv
import random
from pathlib import Path

# بارگذاری متغیرهای محیطی
load_dotenv()

# اطلاعات اینستاگرام
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# تنظیمات MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
MONGO_DB = os.getenv("MONGO_DB", "instagram_bot")
# MONGO_USERNAME = os.getenv("MONGO_USERNAME")
# MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

# تنظیمات API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# تنظیمات بات
BOT_SLEEP_TIME = int(os.getenv("BOT_SLEEP_TIME", "60"))
DAILY_INTERACTION_LIMIT = int(
    os.getenv("DAILY_INTERACTION_LIMIT", "50"))  # کاهش از 100 به 50
COMMENT_PROBABILITY = float(
    os.getenv("COMMENT_PROBABILITY", "0.1"))  # کاهش از 0.3 به 0.1
REACTION_PROBABILITY = float(
    os.getenv("REACTION_PROBABILITY", "0.2"))  # کاهش از 0.5 به 0.2
# کاهش از 0.1 به 0.05
DM_PROBABILITY = float(os.getenv("DM_PROBABILITY", "0.05"))

# فواصل زمانی تصادفی برای رفتار شبیه انسان (به ثانیه)
MIN_ACTION_INTERVAL = 120  # افزایش از 30 به 120
MAX_ACTION_INTERVAL = 480  # افزایش از 180 به 480
MIN_SESSION_DURATION = 3600  # افزایش از 1800 (30 دقیقه) به 3600 (1 ساعت)
MAX_SESSION_DURATION = 10800  # افزایش از 7200 (2 ساعت) به 10800 (3 ساعت)
MIN_BREAK_DURATION = 3600  # افزایش از 1800 (30 دقیقه) به 3600 (1 ساعت)
MAX_BREAK_DURATION = 7200  # افزایش از 3600 (1 ساعت) به 7200 (2 ساعت)

# هشتگ‌های فارسی برای جستجو
PERSIAN_HASHTAGS = [
    "ایران",
    "تهران",
    "عکاسی",
    "طبیعت",
    "هنر",
    "آشپزی",
    "سفر",
    "موسیقی",
    "معماری",
    "کتاب",
    "گردشگری",
    "مد",
    "استایل",
    "غذا",
    "خانواده"
]

# توابع زمان‌بندی تصادفی برای رفتار شبیه انسان


def get_random_interval():
    """بازگرداندن فاصله زمانی تصادفی بین اکشن‌ها به ثانیه"""
    return random.randint(MIN_ACTION_INTERVAL, MAX_ACTION_INTERVAL)


def get_random_session_duration():
    """بازگرداندن مدت زمان تصادفی جلسه به ثانیه"""
    return random.randint(MIN_SESSION_DURATION, MAX_SESSION_DURATION)


def get_random_break_duration():
    """بازگرداندن مدت زمان تصادفی استراحت به ثانیه"""
    return random.randint(MIN_BREAK_DURATION, MAX_BREAK_DURATION)


# دایرکتوری قالب‌ها
TEMPLATES_DIR = Path(__file__).parent / "templates"
