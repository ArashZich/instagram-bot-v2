import os
from dotenv import load_dotenv
import random
from pathlib import Path

# Load environment variables
load_dotenv()

# Instagram credentials
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# MongoDB configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
MONGO_DB = os.getenv("MONGO_DB", "instagram_bot")
# MONGO_USERNAME = os.getenv("MONGO_USERNAME")
# MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Bot configuration
BOT_SLEEP_TIME = int(os.getenv("BOT_SLEEP_TIME", "60"))
DAILY_INTERACTION_LIMIT = int(os.getenv("DAILY_INTERACTION_LIMIT", "100"))
COMMENT_PROBABILITY = float(os.getenv("COMMENT_PROBABILITY", "0.3"))
REACTION_PROBABILITY = float(os.getenv("REACTION_PROBABILITY", "0.5"))
DM_PROBABILITY = float(os.getenv("DM_PROBABILITY", "0.1"))

# Random time intervals for human-like behavior (in seconds)
MIN_ACTION_INTERVAL = 30
MAX_ACTION_INTERVAL = 180
MIN_SESSION_DURATION = 1800  # 30 minutes
MAX_SESSION_DURATION = 7200  # 2 hours
MIN_BREAK_DURATION = 1800  # 30 minutes
MAX_BREAK_DURATION = 3600  # 1 hour

# Random timing functions for human-like behavior


def get_random_interval():
    """Return a random interval between actions in seconds"""
    return random.randint(MIN_ACTION_INTERVAL, MAX_ACTION_INTERVAL)


def get_random_session_duration():
    """Return a random session duration in seconds"""
    return random.randint(MIN_SESSION_DURATION, MAX_SESSION_DURATION)


def get_random_break_duration():
    """Return a random break duration in seconds"""
    return random.randint(MIN_BREAK_DURATION, MAX_BREAK_DURATION)


# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
