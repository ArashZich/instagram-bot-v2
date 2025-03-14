from typing import Dict, List, Tuple, Optional
import re


class ContentAnalyzer:
    """کلاس برای تحلیل محتوا و تشخیص موضوع پست‌ها"""

    def __init__(self):
        # دیکشنری کلمات کلیدی برای هر موضوع به همراه وزن هر کلمه
        self.keywords = {
            "travel": [
                ("سفر", 2), ("گردش", 1.5), ("طبیعت", 1.5), ("دریا", 1), ("کوه", 1),
                ("جنگل", 1), ("منظره", 1), ("توریست", 1.5), ("گردشگری", 2),
                ("تعطیلات", 1.5), ("مسافرت", 2), ("جاده", 1), ("هتل", 1.5),
                ("بلیط", 1), ("پرواز", 1), ("اقامت", 1), ("رزرو", 0.5),
                ("طبیعتگردی", 2), ("بوم‌گردی", 2), ("اکوتوریسم", 2),
                ("ویلا", 1), ("اقامتگاه", 1), ("کمپ", 1), ("کمپینگ", 1)
            ],
            "food": [
                ("غذا", 2), ("خوشمزه", 1.5), ("رستوران", 1.5), ("کافه", 1),
                ("دسر", 1), ("صبحانه", 1), ("ناهار", 1), ("شام", 1),
                ("آشپزی", 2), ("خوراک", 1.5), ("طعم", 1), ("مزه", 1),
                ("رسپی", 1.5), ("دستور پخت", 2), ("آشپز", 1.5), ("پخت و پز", 1.5),
                ("فودی", 1.5), ("کافی‌شاپ", 1), ("سرآشپز", 1.5), ("سنتی", 0.5),
                ("خانگی", 1), ("گورمه", 1.5), ("استیک", 1), ("کباب", 1),
                ("سالاد", 1), ("پیتزا", 1), ("پاستا", 1), ("برگر", 1)
            ],
            "fashion": [
                ("مد", 2), ("لباس", 1.5), ("استایل", 2), ("طراحی", 1),
                ("پوشاک", 1.5), ("ست", 1.5), ("اکسسوری", 1.5), ("برند", 1),
                ("پوشش", 1), ("فشن", 2), ("ترند", 1.5), ("زیبایی", 0.8),
                ("شیک", 1.5), ("خاص", 0.8), ("کفش", 1), ("کیف", 1),
                ("جواهرات", 1), ("بوتیک", 1.5), ("طراح لباس", 2), ("کالکشن", 1.5),
                ("فشن‌بلاگر", 2), ("استایلیست", 2), ("مینیمال", 1),
                ("مکسیمال", 1), ("وینتیج", 1), ("چرم", 0.8)
            ],
            "fitness": [
                ("ورزش", 2), ("تمرین", 2), ("سلامتی", 1.5), ("تناسب اندام", 2),
                ("بدنسازی", 2), ("یوگا", 1.5), ("دویدن", 1), ("پیلاتس", 1.5),
                ("فیتنس", 2), ("باشگاه", 1.5), ("ورزشکار", 1.5), ("عضله", 1.5),
                ("وزنه", 1.5), ("استقامتی", 1.5), ("هوازی", 1.5), ("بی‌هوازی", 1.5),
                ("چربی‌سوزی", 1.5), ("کالری", 1), ("پروتئین", 1), ("مکمل", 1),
                ("رژیم", 1), ("لاغری", 1), ("حجم", 1), ("فرم‌دهی", 1.5),
                ("مربی", 1.5), ("کراس‌فیت", 1.5), ("تی‌آر‌ایکس", 1.5)
            ],
            "art": [
                ("هنر", 2), ("نقاشی", 1.5), ("طراحی", 1.5), ("خلاقیت", 1.5),
                ("موسیقی", 1.5), ("فیلم", 1), ("سینما", 1.5), ("تئاتر", 1.5),
                ("مجسمه", 1.5), ("گالری", 1.5), ("نمایشگاه", 1.5), ("آثار هنری", 2),
                ("هنرمند", 1.5), ("آبستره", 1.5), ("رئالیسم", 1.5), ("سورئال", 1.5),
                ("مدرن", 1), ("کلاسیک", 1), ("کنسرت", 1.5), ("خواننده", 1),
                ("نوازنده", 1.5), ("آهنگساز", 1.5), ("کارگردان", 1.5),
                ("بازیگر", 1), ("فرهنگ", 1), ("ادبیات", 1.5)
            ],
            "photography": [
                ("عکس", 2), ("عکاسی", 2), ("دوربین", 1.5), ("منظره", 1),
                ("پرتره", 1.5), ("نور", 1), ("لنز", 1.5), ("فوکوس", 1.5),
                ("شاتر", 1.5), ("فریم", 1.5), ("کمپوزیسیون", 2), ("عکاس", 1.5),
                ("آتلیه", 1.5), ("استودیو", 1.5), ("فلاش", 1), ("تصویر", 1),
                ("دیافراگم", 1.5), ("سرعت", 1), ("ایزو", 1.5), ("وایدانگل", 1.5),
                ("تله", 1), ("ماکرو", 1.5), ("فتوگرافی", 2), ("مونوکروم", 1.5),
                ("سیاه و سفید", 1.5), ("رنگی", 0.8)
            ],
            "lifestyle": [
                ("زندگی", 1), ("سبک زندگی", 2), ("خانه", 1), ("دکوراسیون", 1.5),
                ("باغبانی", 1.5), ("چیدمان", 1.5), ("مبلمان", 1.5), ("دیزاین", 1.5),
                ("لایف استایل", 2), ("روتین", 1.5), ("روزمره", 1), ("شخصی", 0.8),
                ("خانواده", 1), ("فرزند", 1), ("همسر", 1), ("روابط", 1),
                ("گل‌آرایی", 1.5), ("گیاهان", 1), ("سوکولنت", 1.5), ("تراریوم", 1.5),
                ("آپارتمان", 1), ("ویلا", 1), ("نظافت", 1), ("مرتب", 1),
                ("سازماندهی", 1.5), ("مینیمالیسم", 1.5)
            ],
            "beauty": [
                ("آرایش", 2), ("میکاپ", 2), ("زیبایی", 1.5), ("پوست", 1.5),
                ("مو", 1.5), ("ناخن", 1.5), ("اسکین‌کر", 2), ("کرم", 1),
                ("ماسک", 1), ("شامپو", 1), ("سرم", 1.5), ("رنگ مو", 1.5),
                ("کانتور", 1.5), ("هایلایت", 1.5), ("رژلب", 1), ("خط چشم", 1),
                ("آرایشگاه", 1.5), ("سالن زیبایی", 1.5), ("براشینگ", 1.5),
                ("کراتینه", 1.5), ("لیفت", 1.5), ("لمینت", 1.5), ("بوتاکس", 1.5),
                ("فیلر", 1.5), ("مژه", 1), ("ابرو", 1)
            ],
            "technology": [
                ("تکنولوژی", 2), ("فناوری", 2), ("گجت", 1.5), ("موبایل", 1.5),
                ("لپتاپ", 1.5), ("کامپیوتر", 1.5), ("هوشمند", 1.5), ("اپلیکیشن", 1.5),
                ("نرم‌افزار", 1.5), ("سخت‌افزار", 1.5), ("اینترنت", 1), ("وب", 1),
                ("دیجیتال", 1.5), ("آنلاین", 1), ("شبکه", 1), ("گیم", 1.5),
                ("بازی", 1), ("کنسول", 1.5), ("پلی‌استیشن", 1.5), ("ایکس‌باکس", 1.5),
                ("دوربین", 1), ("تبلت", 1.5), ("ساعت هوشمند", 1.5), ("هدفون", 1),
                ("بلوتوث", 1), ("شارژر", 1)
            ]
        }

        # لیست کلمات عمومی که در تشخیص موضوع نباید تاثیر زیادی داشته باشند
        self.common_words = [
            "خیلی", "چقدر", "است", "هست", "بود", "باشد", "این", "آن",
            "که", "و", "یا", "از", "به", "با", "در", "اما", "ولی",
            "برای", "تا", "هم", "اگر", "پس", "چون", "زیرا", "بنابراین",
            "خوب", "بد", "عالی", "بهتر", "بدتر", "بهترین", "بدترین",
            "من", "تو", "او", "ما", "شما", "آنها", "ایشان"
        ]

    def analyze(self, text: str, hashtags: List[str] = None) -> str:
        """تحلیل متن و تشخیص موضوع آن"""
        if not text and not hashtags:
            return "general"

        # پاکسازی متن
        text = text.lower()

        # ترکیب متن و هشتگ‌ها
        combined_text = text
        if hashtags:
            combined_text += " " + " ".join(hashtags)

        # محاسبه امتیاز هر موضوع
        scores = self._calculate_scores(combined_text)

        # انتخاب موضوع با بیشترین امتیاز
        if scores and max(scores.values()) > 0:
            return max(scores.items(), key=lambda x: x[1])[0]

        return "general"

    def _calculate_scores(self, text: str) -> Dict[str, float]:
        """محاسبه امتیاز هر موضوع براساس کلمات کلیدی"""
        scores = {topic: 0.0 for topic in self.keywords.keys()}

        for topic, words in self.keywords.items():
            for word, weight in words:
                # جستجوی کلمه در متن
                matches = re.findall(r'\b' + re.escape(word) + r'\b', text)
                # اگر کلمه در متن پیدا شد، امتیاز موضوع را افزایش بده
                if matches:
                    # حداکثر 3 مرتبه تکرار در امتیاز تاثیر داشته باشد
                    count = min(len(matches), 3)
                    scores[topic] += weight * count

        return scores

    def get_related_words(self, topic: str) -> List[str]:
        """کلمات مرتبط با یک موضوع را برمی‌گرداند"""
        if topic in self.keywords:
            return [word for word, _ in self.keywords[topic]]
        return []
