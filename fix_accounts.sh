#!/bin/bash
# Script to fix broken accounts

echo "🔧 Fixing broken accounts..."
echo ""

cd /root/tel-panl/TELEGRAM-PANNEL

echo "Step 1: Stopping bot..."
pkill -f "python.*start_bot"
sleep 2

echo "Step 2: Backing up current sessions..."
mkdir -p backup_sessions
mv +*.session backup_sessions/ 2>/dev/null
echo "  ✅ Sessions backed up to backup_sessions/"

echo "Step 3: Cleaning up session database files..."
rm -f *.session-journal 2>/dev/null
echo "  ✅ Cleaned up"

echo "Step 4: Starting bot..."
nohup python3 start_bot.py > bot_running.log 2>&1 &
sleep 8

if ps aux | grep -q "[p]ython3 start_bot"; then
    echo "  ✅ Bot started successfully!"
    echo ""
    echo "=" 
    echo "📋 NEXT STEPS:"
    echo "="
    echo ""
    echo "1. در تلگرام به ربات خود پیام /start بدهید"
    echo "2. روی دکمه 'Account Management' کلیک کنید"
    echo "3. روی 'Add Account' کلیک کنید"
    echo "4. شماره تلفن همراه خود را وارد کنید (با + مثل: +989123456789)"
    echo "5. کد تایید را وارد کنید"
    echo "6. اگر رمز دو مرحله‌ای دارید، آن را وارد کنید"
    echo "7. این مراحل را برای همه اکانت‌هایی که می‌خواهید تکرار کنید"
    echo ""
    echo "⚠️  مهم: حتماً اکانت‌ها را دوباره اضافه کنید تا بتوانند پیام بفرستند"
else
    echo "  ❌ Bot failed to start!"
    tail -30 bot_running.log
fi

