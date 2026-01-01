#!/usr/bin/env python3
print('=' * 60)
print('FINAL BOT SETUP CHECK')
print('=' * 60)

# Test all imports
imports_ok = True
try:
    import telethon
    print('OK telethon imported')
except Exception as e:
    print(f'FAIL telethon failed: {e}')
    imports_ok = False

try:
    from dotenv import load_dotenv
    print('OK dotenv imported')
except Exception as e:
    print(f'FAIL dotenv failed: {e}')
    imports_ok = False

try:
    import asyncio
    print('OK asyncio imported')
except Exception as e:
    print(f'FAIL asyncio failed: {e}')
    imports_ok = False

# Test config loading
config_ok = True
try:
    load_dotenv()
    import os
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    bot_token = os.getenv('BOT_TOKEN')
    admin_id = os.getenv('ADMIN_ID')

    if not all([api_id, api_hash, bot_token, admin_id]):
        print('FAIL Missing config values')
        config_ok = False
    else:
        print('OK Config values loaded')
except Exception as e:
    print(f'FAIL Config loading failed: {e}')
    config_ok = False

# Test bot imports
bot_ok = True
try:
    from src.Config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID
    print('OK Bot config imported')
except Exception as e:
    print(f'FAIL Bot config failed: {e}')
    bot_ok = False

try:
    from src.Telbot import TelegramBot
    print('OK TelegramBot class imported')
except Exception as e:
    print(f'FAIL TelegramBot import failed: {e}')
    bot_ok = False

print()
print('=' * 60)
if imports_ok and config_ok and bot_ok:
    print('SUCCESS BOT SETUP: ALL SYSTEMS GO!')
    print('The bot is ready. Network connectivity is the only remaining issue.')
else:
    print('ERROR BOT SETUP: ISSUES FOUND')
    print('Fix the above errors before network testing.')
print('=' * 60)
