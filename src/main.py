import logging
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
from config import API_ID, API_HASH, BOT_TOKEN, TARGET_GROUPS, KEYWORDS, CHANNEL_ID, IGNORE_USERS, load_json_config, update_json_config
import asyncio
import json
import os
import random

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load clients configuration from JSON
def load_json_config():
    if os.path.exists('clients.json'):
        with open('clients.json', 'r') as f:
            return json.load(f)
    else:
        return {'clients': []}

# Update clients configuration
def update_json_config(config):
    with open('clients.json', 'w') as f:
        json.dump(config, f, indent=4)

# clients
main_client = TelegramClient("krtkmahan", API_ID, API_HASH) # Recive messages
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN) # Sending to Channel
bot2 = TelegramClient("bot2", API_ID, API_HASH).start(bot_token=BOT_TOKEN) # Keyboard

# process incoming messages
async def process_message(event):
    message = event.message.message
    sender_id = event.message.sender_id
    logger.info(f"Received a new message from {sender_id}")

    # Load Vars
    config = load_json_config()
    ignore_users = config['IGNORE_USERS']
    keywords = config['KEYWORDS']

    # Messages loop
    if sender_id in ignore_users:
        logger.info(f"Ignoring message from {sender_id}")
        return
    if any(keyword.lower() in message.lower() for keyword in keywords):
        try:
            user = await event.message.get_sender()
            user_id = user.id

            text = f"• Text:\n{message}\n• ID: `{user_id}`\n"

            if event.chat:
                if event.chat.username:
                    message_link = f"https://t.me/{event.chat.username}/{event.id}"
                else:
                    chat_id = str(event.chat_id).replace('-100', '', 1)
                    message_link = f"https://t.me/c/{chat_id}/{event.message.id}"

                buttons = [
                    [Button.url("View Message", url=message_link)]
                ]
                await bot.send_message(CHANNEL_ID, text, buttons=buttons, link_preview=False)
                logger.info(f"Message forwarded to channel {CHANNEL_ID} with button")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

@main_client.on(events.NewMessage(chats=TARGET_GROUPS))
async def my_event_handler(event):
    await process_message(event)

# Bot2 buttons
@bot2.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline('Update Groups', b'update_groups')],
        [Button.inline('Add Keyword', b'add_keyword'), Button.inline('Remove Keyword', b'remove_keyword')],
        [Button.inline('Ignore User', b'ignore_user')],
        [Button.inline('Remove Ignore User', b'remove_ignore_user')],  # New button added here
    ]
    await event.respond('Management Menu', buttons=buttons)

# Handle button clicks
@bot2.on(events.CallbackQuery)
async def callback(event):
    config = load_json_config()
    # update
    if event.data == b'update_groups':
        await main_client.start()
        dialogs = await main_client.get_dialogs()
        groups = [dialog.entity.id for dialog in dialogs if dialog.is_group]
        config['TARGET_GROUPS'] = groups
        update_json_config(config)
        await event.answer(f"Groups updated: {groups}")
    # ignore user
    elif event.data == b'ignore_user':
        await event.answer('Please enter the user ID to ignore:')
        bot2.add_event_handler(ignore_user_handler)
    # remove ignore user
    elif event.data == b'remove_ignore_user':
        await event.answer('Please enter the user ID to remove from ignore list:')
        bot2.add_event_handler(remove_ignore_user_handler)
    # add keyword
    elif event.data == b'add_keyword':
        await event.answer('Please enter the keyword to add:')
        bot2.add_event_handler(add_keyword_handler)
    # remove keyword
    elif event.data == b'remove_keyword':
        await event.answer('Please enter the keyword to remove:')
        bot2.add_event_handler(remove_keyword_handler)

# Handlers for user inputs
# ignore users
async def ignore_user_handler(event):
    config = load_json_config()
    user_id = int(event.message.message)
    if user_id not in config['IGNORE_USERS']:
        config['IGNORE_USERS'].append(user_id)
        update_json_config(config)
        await event.respond(f"User {user_id} added to ignore list.")
    else:
        await event.respond(f"User {user_id} is already in the ignore list.")
    config = load_json_config()  # Reload config after update
# remove ignore user
async def remove_ignore_user_handler(event):
    config = load_json_config()
    user_id = int(event.message.message)
    if user_id in config['IGNORE_USERS']:
        config['IGNORE_USERS'].remove(user_id)
        update_json_config(config)
        await event.respond(f"User {user_id} removed from ignore list.")
    else:
        await event.respond(f"User {user_id} was not in the ignore list.")
    config = load_json_config()  # Reload config after update
# add keyword
async def add_keyword_handler(event):
    config = load_json_config()
    keyword = event.message.message
    if keyword not in config['KEYWORDS']:
        config['KEYWORDS'].append(keyword)
        update_json_config(config)
        await event.respond(f"Keyword '{keyword}' added.")
    else:
        await event.respond(f"Keyword '{keyword}' already exists.")
    config = load_json_config()  # Reload config after update
# remove keyword
async def remove_keyword_handler(event):
    config = load_json_config()
    keyword = event.message.message
    if keyword in config['KEYWORDS']:
        config['KEYWORDS'].remove(keyword)
        update_json_config(config)
        await event.respond(f"Keyword '{keyword}' removed.")
    else:
        await event.respond(f"Keyword '{keyword}' not found.")
    config = load_json_config()  # Reload config after update

# Start clients
async def start_clients():
    try:
        await main_client.start(phone=lambda: input("Enter your phone number: "))
        logger.info("Client started successfully")
        
        await bot.start()
        logger.info("Bot started successfully")
        
        await main_client.send_message(CHANNEL_ID, "account started")
        await bot.send_message(CHANNEL_ID, "bot started")
        logger.info("Startup messages sent")

        await main_client.run_until_disconnected()

    except SessionPasswordNeededError:
        logger.error("2FA enabled. Please provide the second factor.")
        password = input("Enter your 2FA password: ")
        await main_client.start(password=password)
    except Exception as e:
        logger.error(f"Error starting the client or bot: {e}", exc_info=True)
    finally:
        await main_client.disconnect()
        await bot.disconnect()
        logger.info("Client and bot disconnected")

# Run
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_clients())
    bot2.run_until_disconnected()
