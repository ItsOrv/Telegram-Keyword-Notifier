#!/bin/bash
# Script to check if any accounts were automatically removed

echo "🔍 بررسی ایمنی اکانت‌ها..."
echo ""

cd /root/tel-panl/TELEGRAM-PANNEL

echo "1️⃣ بررسی لاگ‌ها برای حذف اکانت:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REMOVED=$(grep -i "Removing.*session\|deleted.*session\|Removing revoked" bot_running.log 2>/dev/null | tail -10)

if [ -z "$REMOVED" ]; then
    echo "✅ هیچ اکانتی حذف نشده است"
else
    echo "⚠️  اکانت‌های حذف شده:"
    echo "$REMOVED"
fi

echo ""
echo "2️⃣ اکانت‌های فعلی در clients.json:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ACCOUNTS=$(python3 -c "import json; data=json.load(open('clients.json')); print('تعداد اکانت‌ها:', len(data.get('clients', {}))); [print('  •', k) for k in data.get('clients', {}).keys()]" 2>/dev/null)

if [ -z "$ACCOUNTS" ]; then
    echo "❌ هیچ اکانتی یافت نشد"
else
    echo "$ACCOUNTS"
fi

echo ""
echo "3️⃣ فایل‌های session موجود:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SESSION_FILES=$(ls +*.session 2>/dev/null)

if [ -z "$SESSION_FILES" ]; then
    echo "❌ هیچ فایل session یافت نشد"
else
    echo "$SESSION_FILES" | while read line; do
        echo "  ✅ $line"
    done
fi

echo ""
echo "4️⃣ بررسی SessionRevokedError در لاگ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
REVOKED=$(grep -i "SessionRevokedError\|session revoked\|true SessionRevokedError" bot_running.log 2>/dev/null | tail -5)

if [ -z "$REVOKED" ]; then
    echo "✅ هیچ SessionRevokedError یافت نشد"
else
    echo "⚠️  SessionRevokedError یافت شد:"
    echo "$REVOKED"
    echo ""
    echo "💡 این به معنای این است که:"
    echo "   - شما از تلگرام اصلی Logout کرده‌اید"
    echo "   - یا رمز عبور را تغییر داده‌اید"
    echo "   - یا تلگرام session را لغو کرده است"
    echo "   باید دوباره اکانت را اضافه کنید"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ بررسی کامل شد"

