import logging
from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_NAME, TARGET_GROUPS, KEYWORDS, IGNORE_USERS, load_json_config, update_json_config
import asyncio

# Initialize bot
bot = TelegramClient("bot2", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

logging.basicConfig(level=logging.INFO)

# Add "Update Groups" button
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline('Update Groups', b'update_groups')],
        [Button.inline('Add Keyword', b'add_keyword'), Button.inline('Remove Keyword', b'remove_keyword')],
        [Button.inline('Ignore User', b'ignore_user')],
    ]
    await event.respond('Management Menu', buttons=buttons)

# Handle button clicks
@bot.on(events.CallbackQuery)
async def callback(event):
    config = load_json_config()

    if event.data == b'update_groups':
        main_client = TelegramClient("krtkmahan", API_ID, API_HASH)
        await main_client.start()

        dialogs = await main_client.get_dialogs()
        groups = [dialog.entity.id for dialog in dialogs if dialog.is_group]
        config['TARGET_GROUPS'] = groups
        update_json_config(config)
        
        await event.respond(f"Groups updated: {groups}")

    elif event.data == b'ignore_user':
        await event.respond('Please enter the user ID to ignore:')
        bot.add_event_handler(ignore_user_handler)


    elif event.data == b'add_keyword':
        await event.respond('Please enter the keyword to add:')
        bot.add_event_handler(add_keyword_handler)

    elif event.data == b'remove_keyword':
        await event.respond('Please enter the keyword to remove:')
        bot.add_event_handler(remove_keyword_handler)

# Handlers for user inputs
async def ignore_user_handler(event):
    config = load_json_config()
    user_id = int(event.message.message)
    if user_id not in config['IGNORE_USERS']:
        config['IGNORE_USERS'].append(user_id)
        update_json_config(config)
        await event.respond(f"User {user_id} added to ignore list.")
    else:
        await event.respond(f"User {user_id} is already in the ignore list.")

async def add_keyword_handler(event):
    config = load_json_config()
    keyword = event.message.message
    if keyword not in config['KEYWORDS']:
        config['KEYWORDS'].append(keyword)
        update_json_config(config)
        await event.respond(f"Keyword '{keyword}' added.")
    else:
        await event.respond(f"Keyword '{keyword}' already exists.")

async def remove_keyword_handler(event):
    config = load_json_config()
    keyword = event.message.message
    if keyword in config['KEYWORDS']:
        config['KEYWORDS'].remove(keyword)
        update_json_config(config)
        await event.respond(f"Keyword '{keyword}' removed.")
    else:
        await event.respond(f"Keyword '{keyword}' not found.")

# Start the bot
bot.start()
bot.run_until_disconnected()
