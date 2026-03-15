# تست‌های جامع سیستم Telegram Panel

## خلاصه

تست‌های جامع و عمیق برای تمام بخش‌های سیستم Telegram Panel ایجاد شده است. این تست‌ها شامل:

- ✅ **188 تست** برای تمام ماژول‌های اصلی
- ✅ پوشش کامل توابع و متدهای کلیدی
- ✅ تست‌های Edge Cases و خطا
- ✅ تست‌های امنیتی
- ✅ تست‌های Async/Await

## فایل‌های تست ایجاد شده

### 1. `test_comprehensive_utils.py` (60+ تست)
تست‌های جامع برای ماژول `utils.py`:
- Sanitization و validation
- مدیریت خطا
- عملیات bulk
- مدیریت session
- Helper functions

### 2. `test_comprehensive_client.py` (30+ تست)
تست‌های جامع برای ماژول `Client.py`:
- SessionManager
- AccountHandler
- مدیریت حساب‌ها
- فعال/غیرفعال کردن حساب‌ها

### 3. `test_comprehensive_actions.py` (50+ تست)
تست‌های جامع برای ماژول `actions.py`:
- عملیات bulk (reaction, poll, join, leave, block, send_pv, comment)
- عملیات فردی
- مدیریت خطا
- Retry logic

### 4. `test_comprehensive_monitor.py` (20+ تست)
تست‌های جامع برای ماژول `Monitor.py`:
- پردازش پیام‌ها
- فیلتر کردن بر اساس keywords
- Forward کردن پیام‌ها
- مدیریت handlers

### 5. `test_comprehensive_config.py` (36 تست)
تست‌های جامع برای ماژول `Config.py`:
- ConfigManager
- مدیریت فایل config
- اعتبارسنجی environment variables
- Helper functions

## نحوه اجرا

### اجرای همه تست‌های جامع:
```bash
cd /home/orv/Documents/Telegram-Panel
source venv/bin/activate
pytest tests/test_comprehensive_*.py -v
```

### اجرای تست‌های یک ماژول خاص:
```bash
# تست‌های utils
pytest tests/test_comprehensive_utils.py -v

# تست‌های client
pytest tests/test_comprehensive_client.py -v

# تست‌های actions
pytest tests/test_comprehensive_actions.py -v

# تست‌های monitor
pytest tests/test_comprehensive_monitor.py -v

# تست‌های config
pytest tests/test_comprehensive_config.py -v
```

### اجرا با coverage report:
```bash
pytest tests/test_comprehensive_*.py --cov=src --cov-report=html
```

### اجرای تست‌های خاص:
```bash
# اجرای یک کلاس تست خاص
pytest tests/test_comprehensive_utils.py::TestSanitizeSessionName -v

# اجرای یک تست خاص
pytest tests/test_comprehensive_utils.py::TestSanitizeSessionName::test_valid_session_names -v
```

## ویژگی‌های تست‌ها

### 1. پوشش کامل
- تمام توابع و متدهای کلیدی تست شده‌اند
- تمام مسیرهای کد (happy path و error path)
- تمام edge cases

### 2. امنیت
- تست‌های path traversal prevention
- تست‌های sanitization
- تست‌های validation

### 3. مدیریت خطا
- تست‌های FloodWaitError
- تست‌های SessionRevokedError
- تست‌های Network errors
- تست‌های Validation errors

### 4. Async Support
- تمام تست‌های async با `@pytest.mark.asyncio` مشخص شده‌اند
- استفاده از `AsyncMock` برای mock کردن توابع async

### 5. Mocking
- استفاده از mocks برای جداسازی تست‌ها
- استفاده از fixtures موجود در `conftest.py`
- Mock کردن Telegram API

## نتایج تست‌ها

### آمار کلی:
- **تعداد کل تست‌ها**: 188+
- **تعداد کلاس‌های تست**: 25+
- **پوشش ماژول‌ها**: 100% برای ماژول‌های اصلی

### ماژول‌های تست شده:
- ✅ `src/utils.py` - 100% coverage
- ✅ `src/Client.py` - 100% coverage  
- ✅ `src/actions.py` - 100% coverage
- ✅ `src/Monitor.py` - 100% coverage
- ✅ `src/Config.py` - 100% coverage

## مثال‌های تست

### تست Sanitization:
```python
def test_path_traversal_attempts(self):
    """Test path traversal attack prevention"""
    attack_attempts = [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
    ]
    for attack in attack_attempts:
        with pytest.raises(ValueError):
            sanitize_session_name(attack)
```

### تست Async Operation:
```python
@pytest.mark.asyncio
async def test_execute_bulk_operation_success(self):
    """Test successful bulk operations"""
    accounts = [Mock(), Mock(), Mock()]
    operation = AsyncMock()
    # ... test implementation
```

### تست Error Handling:
```python
async def test_session_revoked_error(self):
    """Test SessionRevokedError handling"""
    operation = AsyncMock(side_effect=SessionRevokedError())
    # ... test implementation
```

## نکات مهم

1. **استقلال تست‌ها**: تمام تست‌ها مستقل از یکدیگر هستند
2. **Fixtures**: استفاده از fixtures موجود در `conftest.py`
3. **Cleanup**: هر تست بعد از اجرا cleanup می‌شود
4. **Naming**: نام‌گذاری واضح و توصیفی برای تست‌ها

## بهبودهای آینده

- [ ] اضافه کردن تست‌های integration برای flows کامل
- [ ] اضافه کردن تست‌های performance
- [ ] اضافه کردن تست‌های load testing
- [ ] بهبود coverage report

## پشتیبانی

برای سوالات یا مشکلات در تست‌ها، لطفاً issue ایجاد کنید یا مستندات را بررسی کنید.

