import time
import threading
import os
from loguru import logger
import traceback
import subprocess
import sys

from app.bot.instagram_bot import InstagramBot
from app.config import BOT_SLEEP_TIME


def main():
    """Main function to run the Instagram bot"""
    try:
        # Run network test first
        logger.info("در حال اجرای تست‌های شبکه...")
        result = subprocess.run([sys.executable, "-m", "app.network_test"],
                                capture_output=True, text=True)
        logger.info(result.stdout)

        if result.returncode != 0:
            logger.error("تست‌های شبکه شکست خوردند. برنامه اصلی اجرا نمی‌شود.")
            return

        # Setup the bot
        logger.info("Initializing Instagram bot...")
        bot = InstagramBot()

        # Run the bot continuously
        logger.info("Starting bot in continuous mode...")
        worker_thread = bot.run_continuously()

        # Keep the main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            bot.stop()

        # Wait for the worker thread to finish
        worker_thread.join(timeout=30)
        logger.info("Bot shutdown complete")

    except Exception as e:
        logger.error(f"Error in main function: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # Wait a bit to ensure MongoDB is ready
    time.sleep(5)
    main()
