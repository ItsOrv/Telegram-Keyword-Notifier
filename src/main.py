import logging
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError
from config import API_ID, API_HASH, BOT_TOKEN, TARGET_GROUPS, KEYWORDS, CHANNEL_ID, IGNORE_USERS, load_json_config, update_json_config
import asyncio
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the clients
main_client = TelegramClient("krtkmahan", API_ID, API_HASH)
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot2 = TelegramClient("bot2", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Function to process incoming messages
async def process_message(event):
    message = event.message.message
    sender_id = event.message.sender_id

    logger.info(f"Received a new message from {sender_id}")

    if sender_id in IGNORE_USERS:
        logger.info(f"Ignoring message from {sender_id}")
        return

    if any(keyword.lower() in message.lower() for keyword in KEYWORDS):
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

# Bot 2: Add "Update Groups", "Add Keyword", "Remove Keyword", and "Ignore User" buttons
@bot2.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline('Update Groups', b'update_groups')],
        [Button.inline('Add Keyword', b'add_keyword'), Button.inline('Remove Keyword', b'remove_keyword')],
        [Button.inline('Ignore User', b'ignore_user')],
    ]
    await event.respond('Management Menu', buttons=buttons)

# Handle button clicks for configuration updates
@bot2.on(events.CallbackQuery)
async def callback(event):
    config = load_json_config()

    if event.data == b'update_groups':
        await main_client.start()
        dialogs = await main_client.get_dialogs()
        groups = [dialog.entity.id for dialog in dialogs if dialog.is_group]
        config['TARGET_GROUPS'] = groups
        update_json_config(config)
        await event.respond(f"Groups updated: {groups}")

    elif event.data == b'ignore_user':
        await event.respond('Please enter the user ID to ignore:')
        bot2.add_event_handler(ignore_user_handler)

    elif event.data == b'add_keyword':
        await event.respond('Please enter the keyword to add:')
        bot2.add_event_handler(add_keyword_handler)

    elif event.data == b'remove_keyword':
        await event.respond('Please enter the keyword to remove:')
        bot2.add_event_handler(remove_keyword_handler)

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

# Start the clients
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

# Run the combined script
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_clients())
    bot2.run_until_disconnected()
