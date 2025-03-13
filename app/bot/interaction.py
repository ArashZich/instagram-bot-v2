import random
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from pathlib import Path

from app.config import TEMPLATES_DIR
from app.bot.utils import humanize_text

# Template data for interactions
TOPICS = {
    "general": ["عکس", "طبیعت", "شهر", "مسافرت", "غذا", "ورزش", "هنر", "موسیقی", "فیلم", "کتاب"],
    "travel": ["سفر", "مسافرت", "طبیعت", "دریا", "کوه", "جنگل", "شهر", "روستا"],
    "food": ["غذا", "رستوران", "کافه", "دسر", "صبحانه", "ناهار", "شام", "نوشیدنی"],
    "fashion": ["مد", "لباس", "استایل", "طراحی", "اکسسوری", "رنگ", "ست"],
    "fitness": ["ورزش", "تمرین", "سلامتی", "تناسب اندام", "بدنسازی", "یوگا", "دویدن"],
    "art": ["هنر", "نقاشی", "عکاسی", "طراحی", "خلاقیت", "موسیقی", "فیلم"],
    "photography": ["عکاسی", "عکس", "دوربین", "منظره", "پرتره", "نور"],
    "lifestyle": ["زندگی", "سبک زندگی", "خانه", "دکوراسیون", "باغبانی", "آشپزی"]
}


class InteractionTemplates:
    """Class to manage interaction templates"""

    def __init__(self):
        self.templates_dir = TEMPLATES_DIR
        self.comments = self._load_or_create_templates("comments")
        self.direct_messages = self._load_or_create_templates(
            "direct_messages")
        self.reactions = self._load_or_create_templates("reactions")

    def _load_or_create_templates(self, template_name: str) -> List[Dict[str, Any]]:
        """Load templates from file or create default ones"""
        template_path = self.templates_dir / f"{template_name}.json"

        try:
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # Create default templates
                if template_name == "comments":
                    templates = self._create_default_comments()
                elif template_name == "direct_messages":
                    templates = self._create_default_dms()
                elif template_name == "reactions":
                    templates = self._create_default_reactions()
                else:
                    templates = []

                # Save templates to file
                template_path.parent.mkdir(parents=True, exist_ok=True)
                with open(template_path, "w", encoding="utf-8") as f:
                    json.dump(templates, f, ensure_ascii=False, indent=2)

                return templates
        except Exception as e:
            logger.error(
                f"Error loading or creating {template_name} templates: {e}")
            return []

    def _create_default_comments(self) -> List[Dict[str, Any]]:
        """Create default comment templates"""
        return [
            # عمومی
            {"text": "پست خیلی جالبی بود! 👍", "topics": ["general"]},
            {"text": "عکس فوق‌العاده‌ایه! 📸",
                "topics": ["photography", "general"]},
            {"text": "واقعاً عالی هست 👏", "topics": ["general"]},
            {"text": "چقدر باحال! ✨", "topics": ["general"]},
            {"text": "خیلی خوب بود 👌", "topics": ["general"]},
            {"text": "دوستش داشتم ❤️", "topics": ["general"]},
            {"text": "چقدر قشنگ 😍", "topics": ["general"]},
            {"text": "فوق‌العاده بود 🌟", "topics": ["general"]},

            # سفر
            {"text": "منظره خیلی زیبایی هست! کجا گرفتی این عکس رو؟ 😍🌿",
                "topics": ["travel", "photography"]},
            {"text": "چه جای قشنگی! حتما باید یه روز برم اونجا 🧳✈️",
                "topics": ["travel"]},
            {"text": "سفر خوش بگذره! 🏞️", "topics": ["travel"]},
            {"text": "این منظره واقعاً فوق‌العاده است! 🌄",
                "topics": ["travel", "photography"]},
            {"text": "سفرهای شما همیشه الهام‌بخشه 🌎", "topics": ["travel"]},

            # غذا
            {"text": "این غذا خیلی خوشمزه به نظر میرسه! 😋🍽️",
                "topics": ["food"]},
            {"text": "دستت درد نکنه، هنرمندی! 👨‍🍳👩‍🍳", "topics": ["food"]},
            {"text": "وای چقدر خوشمزه! دستور پختش رو میشه بذاری؟ 🍴",
                "topics": ["food"]},
            {"text": "عالی شده، اشتهام باز شد 😋", "topics": ["food"]},
            {"text": "تزیین غذات فوق‌العادست! 🍲", "topics": ["food"]},

            # مد و لباس
            {"text": "استایلت عالیه! 👕👖", "topics": ["fashion"]},
            {"text": "این ست لباس خیلی بهت میاد 👗", "topics": ["fashion"]},
            {"text": "از کجا می‌تونم این لباس رو پیدا کنم؟ خیلی قشنگه 👚",
                "topics": ["fashion"]},
            {"text": "ست کردن رنگ‌ها عالی بوده 🎨", "topics": ["fashion"]},

            # فیتنس و ورزش
            {"text": "آفرین! تمرین‌هات الهام‌بخشه 💪", "topics": ["fitness"]},
            {"text": "عالی کار میکنی! انرژی گرفتم 🏋️‍♀️",
                "topics": ["fitness"]},
            {"text": "تلاشت قابل تحسینه، ادامه بده 👊", "topics": ["fitness"]},
            {"text": "میشه برنامه تمرینیت رو به اشتراک بذاری؟ 🏃‍♂️",
                "topics": ["fitness"]},

            # هنر و عکاسی
            {"text": "چه عکس هنری قشنگی! دوربینت چیه؟ 📷",
                "topics": ["photography", "art"]},
            {"text": "نور و کادربندی عکست فوق‌العادست 🎞️",
                "topics": ["photography"]},
            {"text": "استعداد هنریت تحسین‌برانگیزه 🎨", "topics": ["art"]},
            {"text": "این اثر خیلی زیباست، تکنیکت عالیه 🖌️",
                "topics": ["art"]},

            # سبک زندگی
            {"text": "چه فضای دنجی! دکوراسیون خونت عالیه 🏡",
                "topics": ["lifestyle"]},
            {"text": "چیدمان خیلی قشنگی داره 🛋️", "topics": ["lifestyle"]},
            {"text": "این ایده رو حتما امتحان می‌کنم، مرسی از اشتراک‌گذاری 💡",
                "topics": ["lifestyle"]},
            {"text": "سلیقه‌ات تو انتخاب وسایل عالیه 🪴",
                "topics": ["lifestyle"]}
        ]

    def _create_default_dms(self) -> List[Dict[str, Any]]:
        """Create default direct message templates"""
        return [
            # معرفی
            {"text": "سلام! پروفایلت خیلی جالب بود. از کارات خوشم اومد 👋",
                "topics": ["introduction"]},
            {"text": "سلام، اتفاقی با پیجت آشنا شدم. محتوای خوبی داری! 😊",
                "topics": ["introduction"]},
            {"text": "سلام! می‌تونم بگم پست‌های جالبی داری، خواستم بیشتر با کارهات آشنا بشم 👀",
                "topics": ["introduction"]},

            # قدردانی
            {"text": "از تعامل و فعالیتت تو پیجم ممنونم! خواستم تشکر کنم ❤️",
                "topics": ["appreciation"]},
            {"text": "مرسی که پست‌هام رو دنبال می‌کنی، قدردان حمایتت هستم 🙏",
                "topics": ["appreciation"]},
            {"text": "کامنت‌های قشنگت همیشه انرژی‌بخشه، ممنون ازت ✨",
                "topics": ["appreciation"]},

            # مشارکت
            {"text": "پست آخرت خیلی جالب بود! نظرت درباره [موضوع مرتبط] چیه؟ 🤔", "topics": [
                "engagement"]},
            {"text": "محتواهای پیجت خیلی الهام‌بخشه. میشه بیشتر درباره [موضوع مرتبط] حرف بزنیم؟ 💭", "topics": [
                "engagement"]},
            {"text": "فکر می‌کنم علایق مشترکی داریم! من هم به [موضوع مرتبط] علاقه دارم 👍", "topics": [
                "engagement"]},

            # همکاری
            {"text": "کارهات خیلی عالیه! فکر کردم شاید بتونیم در آینده روی پروژه‌ای همکاری کنیم 🤝",
                "topics": ["collaboration"]},
            {"text": "پیجت خیلی خوبه. اگه به همکاری در زمینه [موضوع مرتبط] علاقه داری، خوشحال میشم در موردش صحبت کنیم 📩", "topics": [
                "collaboration"]},

            # سوال
            {"text": "سلام! میشه بگی از چه دوربینی برای عکس‌هات استفاده می‌کنی؟ نتایج کارت عالیه 📸",
                "topics": ["question", "photography"]},
            {"text": "دستور پخت [غذای خاص] رو داری؟ دیدم تو پیجت گذاشتی و خیلی خوشمزه به نظر می‌رسید 🍲", "topics": [
                "question", "food"]},
            {"text": "سلام! اون لوکیشن قشنگی که تو استوری گذاشتی کجا بود؟ می‌خوام برای سفر بعدیم برنامه‌ریزی کنم 🧳",
                "topics": ["question", "travel"]}
        ]

    def _create_default_reactions(self) -> List[str]:
        """Create default story reaction templates"""
        return ["❤️", "🔥", "👏", "😍", "👌", "🙌", "🤩", "💯", "🌟", "✨", "🎉", "👍"]

    def get_comment(self, topic: str = None) -> str:
        """Get a random comment, optionally filtered by topic"""
        if topic and topic in TOPICS:
            # Filter comments that include the specified topic
            filtered_comments = [c for c in self.comments if any(
                t in c.get("topics", []) for t in [topic])]
            if filtered_comments:
                return humanize_text(random.choice(filtered_comments)["text"])

        # If no topic specified or no matching comments, return random comment
        return humanize_text(random.choice(self.comments)["text"])

    def get_direct_message(self, topic: str = None) -> str:
        """Get a random direct message, optionally filtered by topic"""
        if topic:
            # Filter DMs that include the specified topic
            filtered_dms = [
                dm for dm in self.direct_messages if topic in dm.get("topics", [])]
            if filtered_dms:
                return humanize_text(random.choice(filtered_dms)["text"])

        # If no topic specified or no matching DMs, return random DM
        return humanize_text(random.choice(self.direct_messages)["text"])

    def get_reaction(self) -> str:
        """Get a random emoji reaction for stories"""
        return random.choice(self.reactions)

    def get_random_topic(self, category: str = None) -> str:
        """Get a random topic, optionally filtered by category"""
        if category and category in TOPICS:
            return random.choice(TOPICS[category])

        # If no category specified, return random topic from any category
        all_topics = []
        for topic_list in TOPICS.values():
            all_topics.extend(topic_list)

        return random.choice(all_topics)


# Create instance for easy import elsewhere
templates = InteractionTemplates()
