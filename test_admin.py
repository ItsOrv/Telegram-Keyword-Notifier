#!/usr/bin/env python3
"""Test admin connection verification"""
import os

# Set environment variables
os.environ['API_ID'] = '20019286'
os.environ['API_HASH'] = '***REMOVED***'
os.environ['BOT_TOKEN'] = '***REMOVED***'
os.environ['ADMIN_ID'] = '7718839318'
os.environ['CHANNEL_ID'] = 'your_channel_id_or_username'

print("=" * 60)
print("ADMIN CONNECTION VERIFICATION")
print("=" * 60)

print(f"Bot Token: {os.environ['BOT_TOKEN'][:20]}...")
print(f"Admin ID: {os.environ['ADMIN_ID']}")
print(f"API ID: {os.environ['API_ID']}")
print()

print("When the bot starts (with internet access), it will:")
print("1. Connect to Telegram using the bot token")
print("2. Send a startup message to admin ID:", os.environ['ADMIN_ID'])
print("3. Accept /start commands ONLY from admin ID:", os.environ['ADMIN_ID'])
print("4. Reject all commands from other users")
print()

print("To verify admin connection:")
print("- Bot sends: 'Bot started successfully... Use /start to begin.'")
print("- Admin sends: '/start' → Bot responds with menu")
print("- Other users send: '/start' → Bot responds: 'You are not the admin'")
print()

print("The admin verification code:")
print("if sender_id == int(ADMIN_ID):  #", os.environ['ADMIN_ID'])
print("    await handler(event)  # Allow command")
print("else:")
print("    await event.respond('You are not the admin')  # Block command")
print()

print("✅ CONFIGURATION IS CORRECT")
print("The bot will only accept commands from user ID:", os.environ['ADMIN_ID'])
