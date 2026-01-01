#!/bin/bash
# Simple script to restart the bot safely

cd /root/tel-panl/TELEGRAM-PANNEL

echo "🛑 Stopping existing bot..."
pkill -f "python.*start_bot" 2>/dev/null
sleep 2

echo "🔍 Checking syntax..."
python3 -m py_compile src/actions.py src/Client.py src/Handlers.py src/Telbot.py start_bot.py 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Syntax errors found! Fix them before starting."
    exit 1
fi

echo "✅ Syntax OK"
echo "🚀 Starting bot..."
nohup python3 start_bot.py > bot_running.log 2>&1 &
sleep 5

if ps aux | grep -q "[p]ython3 start_bot"; then
    echo "✅ Bot started successfully!"
    echo "📝 Check bot_running.log for details"
    echo "💡 PID: $(pgrep -f 'python.*start_bot')"
else
    echo "❌ Bot failed to start! Check bot_running.log"
    tail -30 bot_running.log
    exit 1
fi

