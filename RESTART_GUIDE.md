# راهنمای Restart کردن ربات

## روش 1: استفاده از اسکریپت verify_and_start.py (توصیه می‌شود)

این اسکریپت قبل از start کردن ربات، syntax و imports را بررسی می‌کند:

```bash
cd /root/tel-panl/TELEGRAM-PANNEL
python3 verify_and_start.py
```

## روش 2: استفاده از اسکریپت restart_bot.sh

```bash
cd /root/tel-panl/TELEGRAM-PANNEL
./restart_bot.sh
```

## روش 3: Restart دستی

```bash
cd /root/tel-panl/TELEGRAM-PANNEL

# 1. متوقف کردن ربات قبلی
pkill -f "python.*start_bot"

# 2. بررسی syntax
python3 -m py_compile src/actions.py src/Client.py src/Handlers.py src/Telbot.py

# 3. Start کردن ربات
nohup python3 start_bot.py > bot_running.log 2>&1 &

# 4. بررسی وضعیت
ps aux | grep "[p]ython3 start_bot"
tail -30 bot_running.log
```

## بررسی وضعیت ربات

```bash
# بررسی اینکه ربات در حال اجرا است
ps aux | grep "[p]ython3 start_bot"

# مشاهده لاگ‌های اخیر
tail -50 bot_running.log

# مشاهده خطاها
grep -i error bot_running.log | tail -20
```

## نکات مهم

1. **همیشه قبل از start کردن، ربات قبلی را متوقف کنید**
2. **Syntax را بررسی کنید** تا مطمئن شوید کد بدون خطا است
3. **بعد از start، لاگ‌ها را بررسی کنید** تا مطمئن شوید ربات به درستی کار می‌کند
4. **اگر ربات start نمی‌شود، لاگ‌ها را بررسی کنید** برای پیدا کردن مشکل

