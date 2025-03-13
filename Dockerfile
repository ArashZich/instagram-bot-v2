FROM python:3.9-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب ابزارهای ضروری شبکه (برای تست)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌های مورد نیاز
COPY requirements.txt .
COPY app/ ./app/

# نصب پکیج‌های مورد نیاز
RUN pip install --no-cache-dir -r requirements.txt

# ایجاد دایرکتوری برای لاگ‌ها و داده‌ها
RUN mkdir -p logs data

# باز کردن پورت API
EXPOSE 8000

# اجرای برنامه
CMD ["python", "-m", "app.main"]