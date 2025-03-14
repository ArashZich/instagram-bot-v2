# بات اینستاگرام نسخه 2

بات اینستاگرام نسخه 2 یک ابزار هوشمند برای تعامل خودکار با کاربران اینستاگرام است که می‌تواند به صورت هوشمند فعالیت‌هایی مانند کامنت‌گذاری، لایک، فالو و آنفالو، واکنش به استوری‌ها و ارسال پیام‌های مستقیم را مدیریت کند. این بات همچنین دارای یک رابط API است که به شما امکان می‌دهد عملکرد بات را نظارت کرده و گزارش‌های دقیقی از فعالیت‌های آن دریافت کنید.

## ویژگی‌های اصلی

- **تعامل هوشمند**: تعامل هوشمند با پست‌ها، استوری‌ها و کاربران اینستاگرام
- **تشخیص محتوای فارسی**: اولویت‌دهی به محتواهای فارسی برای تعامل
- **مدیریت دنبال‌کنندگان**: مدیریت خودکار فالو و آنفالو
- **رفتار انسان‌گونه**: شبیه‌سازی رفتار انسانی با استراحت‌های تصادفی
- **داشبورد مدیریت**: API کامل برای نظارت و مدیریت عملکرد بات
- **ذخیره‌سازی مستمر**: ثبت و ذخیره تمامی فعالیت‌ها در پایگاه داده
- **تحلیل محتوا**: تشخیص خودکار موضوع محتوا برای ارسال کامنت‌های مرتبط

## معماری سیستم

```mermaid
graph TB
    subgraph "اینستاگرام"
        IG[اینستاگرام API]
    end
    
    subgraph "کانتینرها"
        BOT[بات اینستاگرام] --> IG
        API[API مدیریت] --> DB
        BOT --> DB
    end
    
    subgraph "پایگاه داده"
        DB[(MongoDB)]
    end
    
    subgraph "کاربر"
        UI[رابط کاربری وب] --> API
    end
    
    BOT -- "گزارش وضعیت" --> DB
    BOT -- "ثبت تعاملات" --> DB
    API -- "دریافت آمار" --> DB
```

## ساختار پروژه

```mermaid
graph LR
    A[instagram-bot-v2] --> B[app]
    A --> C[data]
    A --> D[logs]
    A --> E[Dockerfile]
    A --> F[docker-compose.yml]
    A --> G[requirements.txt]
    
    B --> H[api]
    B --> I[bot]
    B --> J[database]
    B --> K[templates]
    B --> L[config.py]
    B --> M[main.py]
    
    H --> N[routes.py]
    H --> O[schemas.py]
    
    I --> P[actions.py]
    I --> Q[explorers.py]
    I --> R[instagram_bot.py]
    I --> S[session_manager.py]
    I --> T[utils.py]
    I --> U[content_analyzer.py]
    I --> V[interaction.py]
    
    J --> W[connection.py]
    J --> X[models.py]
    
    K --> Y[comments.json]
    K --> Z[direct_messages.json]
    K --> AA[reactions.json]
```

## گردش کار بات

```mermaid
sequenceDiagram
    participant Bot as بات اینستاگرام
    participant Instagram as اینستاگرام
    participant DB as پایگاه داده
    
    Bot->>Bot: راه‌اندازی و تنظیم پارامترها
    Bot->>Instagram: ورود به حساب کاربری
    Bot->>DB: ثبت شروع جلسه
    
    loop هر جلسه
        Bot->>Instagram: بررسی دنبال‌کنندگان
        Instagram-->>Bot: دریافت لیست دنبال‌کنندگان
        Bot->>DB: به‌روزرسانی اطلاعات دنبال‌کنندگان
        
        alt تعامل با هشتگ‌ها
            Bot->>Instagram: جستجوی پست‌ها با هشتگ‌های فارسی
            Instagram-->>Bot: دریافت پست‌ها
            Bot->>Instagram: کامنت یا لایک برای پست‌های منتخب
            Bot->>DB: ثبت تعامل
        end
        
        alt بررسی تایم‌لاین
            Bot->>Instagram: دریافت پست‌های تایم‌لاین
            Instagram-->>Bot: لیست پست‌ها
            Bot->>Instagram: تعامل با پست‌های منتخب
            Bot->>DB: ثبت تعامل
        end
        
        alt بررسی استوری‌ها
            Bot->>Instagram: دریافت استوری‌های دنبال‌شوندگان
            Instagram-->>Bot: لیست استوری‌ها
            Bot->>Instagram: ارسال واکنش به استوری‌های منتخب
            Bot->>DB: ثبت تعامل
        end
        
        alt تعامل با دنبال‌کنندگان
            Bot->>DB: دریافت دنبال‌کنندگان بدون تعامل اخیر
            Bot->>Instagram: ارسال پیام مستقیم به کاربران منتخب
            Bot->>DB: ثبت تعامل
        end
        
        Bot->>Bot: استراحت تصادفی بین اکشن‌ها
    end
    
    Bot->>DB: ثبت پایان جلسه
    Bot->>Bot: استراحت تصادفی بین جلسات
```

## معماری API

```mermaid
graph TB
    API[API اصلی]
    API --> A[/بررسی سلامت/]
    API --> B[/تعاملات/]
    API --> C[/کاربران/]
    API --> D[/آمار/]
    API --> E[/عملکرد/]
    API --> F[/کنترل بات/]
    
    B --> B1[دریافت تعاملات]
    B --> B2[دریافت تعامل خاص]
    
    C --> C1[دریافت کاربران]
    C --> C2[دریافت کاربر خاص]
    C --> C3[دریافت تعاملات کاربر]
    
    D --> D1[دریافت آمار کلی]
    
    E --> E1[آمار عملکرد]
    E --> E2[زمان اجرا]
    
    F --> F1[شروع بات]
    F --> F2[توقف بات]
```

## راه‌اندازی

### پیش‌نیازها

- Docker و Docker Compose
- دسترسی به اینترنت
- حساب کاربری اینستاگرام
- Python 3.9+ (برای اجرا بدون داکر)

### نصب و راه‌اندازی

1. کلون کردن مخزن:

```bash
git clone https://github.com/username/instagram-bot-v2.git
cd instagram-bot-v2
```

2. ایجاد فایل `.env` با مقادیر مناسب:

```
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
MONGO_URI=mongodb://mongodb:27017/
MONGO_DB=instagram_bot
API_PORT=8000
```

3. راه‌اندازی با Docker Compose:

```bash
docker-compose up -d
```

این دستور سه سرویس را راه‌اندازی می‌کند:
- MongoDB: پایگاه داده
- Instagram Bot: بات اصلی
- API: رابط مدیریت

## رابط API

API بر روی پورت مشخص شده در فایل `.env` (پیش‌فرض: 8000) در دسترس خواهد بود:

```
http://localhost:8000
```

### نقاط پایانی مهم

- `/`: بررسی سلامت API
- `/interactions/`: دریافت تعاملات انجام شده
- `/users/`: دریافت لیست کاربران
- `/stats`: دریافت آمار کلی بات
- `/performance/stats`: دریافت آمار عملکرد بات
- `/performance/runtime`: دریافت اطلاعات زمان اجرای بات
- `/bot/start`: شروع بات
- `/bot/stop`: توقف بات

## کلاس‌های اصلی

```mermaid
classDiagram
    class InstagramBot {
        +run_session()
        +run_continuously()
        +stop()
        -check_and_update_followers()
        -_update_user_profile()
    }
    
    class SessionManager {
        +login()
        +record_session_start()
        +record_session_end()
        -handle_challenge()
    }
    
    class InstagramActions {
        +follow_user()
        +unfollow_user()
        +comment_on_media()
        +react_to_story()
        +send_direct_message()
        -_record_interaction()
    }
    
    class InstagramExplorers {
        +explore_hashtags()
        +explore_timeline()
        +check_stories()
        +interact_with_followers()
    }
    
    class ContentAnalyzer {
        +analyze()
        +get_related_words()
        -_calculate_scores()
    }
    
    InstagramBot --|> SessionManager : وراثت
    InstagramBot "1" *-- "1" InstagramActions : استفاده
    InstagramBot "1" *-- "1" InstagramExplorers : استفاده
    InstagramActions "1" *-- "1" ContentAnalyzer : استفاده
    InstagramExplorers "1" *-- "1" InstagramActions : استفاده
```

## مدل‌های داده

```mermaid
erDiagram
    BotSession {
        string session_id
        datetime started_at
        datetime ended_at
        string user_agent
        object session_data
        boolean is_active
    }
    
    UserInteraction {
        string user_id
        string username
        enum interaction_type
        datetime timestamp
        string content
        string media_id
        string status
        string error
        object metadata
    }
    
    UserProfile {
        string user_id
        string username
        string full_name
        boolean is_following
        boolean is_follower
        int interaction_count
        datetime last_interaction
        datetime first_seen
        object metadata
    }
    
    BotSession ||--o{ UserInteraction : "has"
    UserProfile ||--o{ UserInteraction : "receives"
```

## تنظیمات و پیکربندی

تنظیمات اصلی بات در فایل `app/config.py` قرار دارد:

- `INSTAGRAM_USERNAME` و `INSTAGRAM_PASSWORD`: اطلاعات ورود به حساب اینستاگرام
- `DAILY_INTERACTION_LIMIT`: محدودیت تعداد تعاملات روزانه
- `COMMENT_PROBABILITY`، `REACTION_PROBABILITY`، `DM_PROBABILITY`: احتمال انجام انواع تعامل
- `MIN_ACTION_INTERVAL` و `MAX_ACTION_INTERVAL`: محدوده زمانی استراحت بین اکشن‌ها
- `MIN_SESSION_DURATION` و `MAX_SESSION_DURATION`: محدوده زمانی طول هر جلسه
- `PERSIAN_HASHTAGS`: لیست هشتگ‌های فارسی مورد استفاده

## ایمنی و امنیت

- بات با رفتاری انسانی و استراحت‌های تصادفی، از محدودیت‌های اینستاگرام جلوگیری می‌کند
- سیستم مدیریت چالش‌های امنیتی اینستاگرام وجود دارد
- محدودیت تعداد تعاملات ساعتی و روزانه برای جلوگیری از شناسایی بات
- ذخیره‌سازی نشست برای بازیابی سریع در صورت قطع اتصال
- تلاش مجدد هوشمند در صورت برخورد با خطا

## لاگ‌گیری

لاگ‌های سیستم در پوشه `logs` ذخیره می‌شوند:
- لاگ‌های روزانه: `logs/instagram_bot_YYYY-MM-DD.log`
- لاگ‌های خطا: `logs/errors_YYYY-MM-DD.log`

## توسعه و مشارکت

برای توسعه این پروژه:

1. ابتدا مخزن را فورک کنید
2. یک شاخه جدید برای قابلیت یا رفع باگ ایجاد کنید
3. تغییرات خود را اعمال کنید
4. درخواست ادغام (Pull Request) ارسال کنید

## ملاحظات قانونی

استفاده از بات‌ها برای تعامل خودکار با اینستاگرام ممکن است برخلاف شرایط و قوانین استفاده از اینستاگرام باشد. مسئولیت استفاده از این بات بر عهده کاربر است.

## خطایابی و رفع مشکلات

در صورت برخورد با مشکل:

1. لاگ‌های سیستم را بررسی کنید
2. اطمینان حاصل کنید MongoDB در دسترس است
3. اطمینان حاصل کنید اطلاعات ورود اینستاگرام صحیح است
4. اینترنت و دسترسی به API اینستاگرام را بررسی کنید
5. از تست شبکه با اجرای `python -m app.network_test` استفاده کنید

## پشتیبانی و ارتباط

برای گزارش مشکلات، از بخش Issues در GitHub استفاده کنید یا به آدرس ایمیل arashzich1992@gmail.com پیام ارسال کنید.