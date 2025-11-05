# راهنمای سریع شروع کار
## Quick Start Guide

این راهنما مراحل سریع راه‌اندازی سیستم را توضیح می‌دهد.

---

## 🚀 نصب و راه‌اندازی / Installation

### مرحله 1: دانلود پروژه
```bash
cd /path/to/your/directory
# اگر از git استفاده می‌کنید:
git pull
```

### مرحله 2: ایجاد Virtual Environment
```bash
# ایجاد virtual environment
python -m venv venv

# فعال‌سازی در Linux/Mac:
source venv/bin/activate

# یا فعال‌سازی در Windows:
venv\Scripts\activate
```

### مرحله 3: نصب Dependencies
```bash
pip install -r requirements.txt
```

✅ باید پیام‌های زیر را ببینید:
- Successfully installed telethon-1.36.0
- Successfully installed python-dotenv-1.0.0
- Successfully installed aiohttp
- Successfully installed requests
- Successfully installed pysocks

---

## ⚙️ تنظیمات / Configuration

### مرحله 4: ایجاد فایل `.env`
```bash
# کپی کردن فایل نمونه
cp env.example .env

# ویرایش فایل
nano .env  # یا vi یا هر ویرایشگر دیگر
```

### مرحله 5: پر کردن اطلاعات

باید این اطلاعات را در `.env` وارد کنید:

#### 1. دریافت API_ID و API_HASH:
- به https://my.telegram.org/apps بروید
- با شماره تلگرام خود وارد شوید
- روی "API development tools" کلیک کنید
- اطلاعات `api_id` و `api_hash` را کپی کنید

```env
API_ID=12345678
API_HASH=your_api_hash_here
```

#### 2. دریافت BOT_TOKEN:
- به @BotFather در تلگرام پیام دهید
- دستور `/newbot` را ارسال کنید
- نام و username برای ربات انتخاب کنید
- token دریافتی را کپی کنید

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

#### 3. دریافت ADMIN_ID:
- به @userinfobot در تلگرام پیام دهید
- user ID خود را کپی کنید

```env
ADMIN_ID=123456789
```

#### 4. ایجاد کانال:
- یک کانال در تلگرام بسازید
- ربات را به کانال اضافه کنید و Admin کنید
- username کانال یا ID آن را وارد کنید

```env
CHANNEL_ID=@your_channel_username
# یا
CHANNEL_ID=-1001234567890
```

### مثال `.env` کامل:
```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=987654321
CHANNEL_ID=@mychannel
BOT_SESSION_NAME=bot_session
CLIENTS_JSON_PATH=clients.json
RATE_LIMIT_SLEEP=60
GROUPS_BATCH_SIZE=10
GROUPS_UPDATE_SLEEP=60
```

---

## ✅ تست سیستم / Testing

### مرحله 6: اجرای تست‌ها
```bash
python test_system.py
```

✅ باید این پیام را ببینید:
```
🎉 ALL TESTS PASSED! System is ready for production.
Total Tests Run: 71
✅ Total Passed: 71
❌ Total Failed: 0
Success Rate: 100.0%
```

---

## 🎬 اجرای ربات / Running the Bot

### مرحله 7: اجرای ربات
```bash
python main.py
```

✅ پیام‌های موفقیت:
```
[INFO] Bot initialized successfully
[INFO] Bot started successfully and all clients have been detected
[INFO] Bot is running...
```

### مرحله 8: استفاده از ربات

1. **شروع کار:**
   - به ربات خود در تلگرام پیام دهید
   - دستور `/start` را بفرستید
   - منوی اصلی را خواهید دید

2. **اضافه کردن اکانت:**
   - Account Management → Add Account
   - شماره تلگرام را وارد کنید
   - کد تایید را وارد کنید
   - اگر 2FA دارید، رمز را وارد کنید

3. **به‌روزرسانی گروه‌ها:**
   - Monitor Mode → Update Groups
   - صبر کنید تا گروه‌ها شناسایی شوند

4. **تنظیم Keywords:**
   - Monitor Mode → Add Keyword
   - کلمات کلیدی مورد نظر را اضافه کنید

5. **شروع مانیتورینگ:**
   - پیام‌های حاوی keywords به کانال شما فوروارد می‌شوند!

---

## 📊 نظارت / Monitoring

### مشاهده Logs:
```bash
# مشاهده real-time
tail -f logs/bot.log

# مشاهده 50 خط آخر
tail -50 logs/bot.log

# جستجو در logs
grep "ERROR" logs/bot.log
```

### بررسی وضعیت:
```bash
# بررسی running process
ps aux | grep main.py

# بررسی استفاده از CPU/Memory
htop  # یا top
```

---

## 🔧 Troubleshooting

### مشکل: ربات شروع نمی‌شود
```bash
# بررسی کنید که virtual environment فعال است
which python  # باید path به venv اشاره کند

# بررسی dependencies
pip list | grep telethon

# بررسی فایل .env
cat .env
```

### مشکل: خطای API_ID یا API_HASH
- مطمئن شوید از https://my.telegram.org/apps دریافت کرده‌اید
- بدون علامت نقل قول در .env بنویسید
- بدون فاصله اضافی

### مشکل: ربات پاسخ نمی‌دهد
- ADMIN_ID را با @userinfobot چک کنید
- مطمئن شوید BOT_TOKEN صحیح است
- logs را بررسی کنید: `tail -f logs/bot.log`

### مشکل: پیام‌ها فوروارد نمی‌شوند
- مطمئن شوید Keywords اضافه کرده‌اید
- گروه‌ها را update کنید
- بررسی کنید اکانت‌ها active هستند
- ربات باید در CHANNEL_ID ادمین باشد

---

## 🛑 توقف ربات / Stopping the Bot

### متوقف کردن:
```bash
# در terminal که ربات در آن اجرا شده:
Ctrl + C

# یا kill از terminal دیگر:
pkill -f main.py
```

### راه‌اندازی مجدد:
```bash
python main.py
```

---

## 📚 منابع اضافی / Additional Resources

- **README.md**: مستندات کامل
- **TEST_REPORT.md**: گزارش تست‌ها
- **DEEP_ANALYSIS_REPORT.md**: تحلیل عمیق سیستم
- **CHANGELOG.md**: تاریخچه تغییرات
- **IMPROVEMENTS_SUMMARY.md**: خلاصه بهبودها

---

## 🎉 موفق باشید!

سیستم شما اکنون آماده است. از امکانات زیر لذت ببرید:
- ✅ مانیتورینگ پیام‌ها
- ✅ مدیریت چندین اکانت
- ✅ عملیات bulk
- ✅ فیلتر هوشمند
- ✅ گزارش‌دهی دقیق

**سوالی دارید؟** به README.md مراجعه کنید یا logs را بررسی کنید.

---

**نویسنده:** AI Assistant  
**تاریخ:** 2025-10-21  
**نسخه:** 1.0.0

