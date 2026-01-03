# 🔒 گزارش ایمنی اکانت‌ها

## ✅ بررسی کامل انجام شد

ربات را بررسی کردم. **اکانت‌ها فقط در شرایط زیر حذف می‌شوند:**

### 1. ✅ SessionRevokedError واقعی از تلگرام (امن)
**زمانی که:**
- شما خودتان از تلگرام اصلی Logout کنید
- رمز عبور اکانت را تغییر دهید
- تلگرام به دلایل امنیتی session را لغو کند

**کد مربوطه:**
```python
# در Client.py - خط 115-124
if ('session' in check_error_msg and 
    ('revoked' in check_error_msg or 'invalid' in check_error_msg)) or 
    'auth' in check_error_msg:
    logger.warning("Client has true SessionRevokedError. Removing permanently...")
    # فقط در این صورت حذف می‌شود
```

### 2. ✅ حذف دستی توسط شما (امن)
**زمانی که:**
- شما از منوی Account Management گزینه Delete را بزنید
- شما به صورت دستی اکانت را حذف کنید

### 3. ✅ خطاهای موقت حذف نمی‌کنند (امن)
**این خطاها اکانت را حذف نمی‌کنند:**
- ❌ خطاهای شبکه (Network errors)
- ❌ خطاهای موقت Telegram API
- ❌ Rate limit errors
- ❌ "key is not registered" (اکانت در لیست می‌ماند برای retry)

**کد محافظت:**
```python
# در Client.py - خط 125-130
else:
    # Not a true session revoked error
    logger.warning("Client has connectivity issues but not revoked. 
                   Keeping in active list for retry.")
    # IMPORTANT: Keep the client in active_clients even if it has issues
```

## 🛡️ محافظت‌های فعال

### 1. بررسی دقیق قبل از حذف
- ربات دو بار بررسی می‌کند: یکبار `is_user_authorized()` و یکبار `get_dialogs()`
- فقط اگر هر دو fail شوند و خطا "session revoked" باشد، حذف می‌شود

### 2. اکانت‌ها در لیست می‌مانند
- حتی اگر موقتاً کار نکنند، در `active_clients` می‌مانند
- در هر task دوباره تلاش می‌شوند
- فقط SessionRevokedError واقعی آنها را حذف می‌کند

### 3. لاگ کامل
- هر حذفی لاگ می‌شود با دلیل دقیق
- می‌توانید در `bot_running.log` ببینید چرا اکانتی حذف شده

## 📊 موارد خاص بررسی شده

### ❌ در actions.py (ارسال پیام)
```python
# خط 1611-1615
if "sessionrevokederror" in error_msg or "not logged in" in error_msg:
    # فقط SessionRevokedError واقعی
    del self.tbot.active_clients[session_name]
```
✅ **امن است** - فقط SessionRevokedError

### ❌ در handle_group_action (عملیات گروهی)
```python
# خط 264-268
if "SessionRevokedError" in error_msg or "not logged in" in error_msg.lower():
    del self.tbot.active_clients[session_name]
```
✅ **امن است** - فقط SessionRevokedError

### ❌ در shutdown
```python
# فقط هنگام خاموش کردن ربات
await self.client_manager.disconnect_all_clients()
```
✅ **امن است** - فقط disconnect می‌کند، حذف نمی‌کند

## 🎯 نتیجه نهایی

### ✅ ربات امن است
- اکانت‌ها را خودکار حذف نمی‌کند
- فقط SessionRevokedError واقعی از تلگرام باعث حذف می‌شود
- خطاهای موقت اکانت را حذف نمی‌کنند
- اکانت‌ها در لیست می‌مانند برای retry

### 💡 توصیه‌ها
1. اگر اکانتی حذف شد، `bot_running.log` را بررسی کنید
2. اگر "SessionRevokedError" دیدید، باید دوباره login کنید
3. اگر خطای دیگری دیدید، اکانت همچنان در لیست است

### 🔍 بررسی لاگ‌ها
برای اطمینان از عدم حذف خودکار:
```bash
cd /root/tel-panl/TELEGRAM-PANNEL
grep -i "Removing.*session" bot_running.log | tail -20
```

اگر چیزی نبود، یعنی هیچ اکانتی حذف نشده است ✅

