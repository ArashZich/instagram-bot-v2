import requests
import socket
import time
import sys


def test_internet():
    try:
        print("تست دسترسی به اینترنت...")
        response = requests.get("https://www.google.com", timeout=10)
        print(f"✅ دسترسی به اینترنت موفق: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ خطا در دسترسی به اینترنت: {e}")
        return False


def test_mongo():
    try:
        print("تست دسترسی به مونگو...")
        sock = socket.create_connection(("mongodb", 27017), timeout=5)
        sock.close()
        print("✅ دسترسی به مونگو موفق")
        return True
    except Exception as e:
        print(f"❌ خطا در دسترسی به مونگو: {e}")
        return False


def test_instagram_api():
    try:
        print("تست دسترسی به API اینستاگرام...")
        response = requests.get("https://www.instagram.com", timeout=10)
        print(f"✅ دسترسی به اینستاگرام موفق: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ خطا در دسترسی به اینستاگرام: {e}")
        return False


if __name__ == "__main__":
    print("شروع تست‌های شبکه...")
    internet = test_internet()
    mongo = test_mongo()
    instagram = test_instagram_api()

    print("\nنتایج تست:")
    print(f"- دسترسی به اینترنت: {'✅' if internet else '❌'}")
    print(f"- دسترسی به مونگو: {'✅' if mongo else '❌'}")
    print(f"- دسترسی به اینستاگرام: {'✅' if instagram else '❌'}")

    if not (internet and mongo):
        print("\n❌ تست‌های پایه شکست خوردند. برنامه اصلی اجرا نخواهد شد.")
        sys.exit(1)

    print("\n✅ همه تست‌ها موفق بودند. آماده اجرای برنامه اصلی.")
