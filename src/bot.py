import logging
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from config import API_ID, API_HASH, BOT_TOKEN, TARGET_GROUPS, KEYWORDS, CHANNEL_ID, IGNORE_USERS
import asyncio
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main_client = TelegramClient("krtkmahan", API_ID, API_HASH)
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def process_message(event):
    message = event.message.message
    sender_id = event.message.sender_id

    logger.info(f"Received a new message from {sender_id}")

    # Ignore messages from specific users
    if sender_id in IGNORE_USERS:
        logger.info(f"Ignoring message from {sender_id}")
        return

    # Check for keywords
    if any(keyword.lower() in message.lower() for keyword in KEYWORDS):
        try:
            user = await event.message.get_sender()
            user_username = user.username if user.username else str(user.id)

            # Initialize the text with basic information
            text = f"• Text:\n{message}\n• ID: @{user_username}\n"
            logger.info(f"Constructed message: {text}")

            # Construct message link if possible
            if event.chat:
                if event.chat.username:
                    message_link = f"https://t.me/{event.chat.username}/{event.id}"
                    text += f"• Link: {message_link}\n\n"
                else:
                    chat_id = str(event.chat_id).lstrip('-100')
                    message_link = f"https://t.me/c/{chat_id}/{event.message.id}"
                    text += f"• Link: {message_link}\n\n"
            else:
                text += "\n"

            # **Send the message using the correct client (client instead of bot)**
            logger.info(f"Attempting to send message to channel: {CHANNEL_ID}")
            await main_client.send_message(CHANNEL_ID, text, link_preview=False)  # Use 'client' for account
            logger.info(f"Message forwarded to channel {CHANNEL_ID}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

# Event handler for new messages
@main_client.on(events.NewMessage(chats=TARGET_GROUPS))
async def my_event_handler(event):
    await process_message(event)

async def start_clients():
    try:
        # Start the client with phone number interaction if needed
        await main_client.start(phone=lambda: input("Enter your phone number: "))
        logger.info("Client started successfully")
        
        # Start the bot
        await bot.start()
        logger.info("Bot started successfully")

        # Send startup messages (make sure account messages use 'client')
        await main_client.send_message(CHANNEL_ID, "account started")  # Send from account
        logger.info("Sent 'account started' message from account")

        await bot.send_message(CHANNEL_ID, "bot started")  # Send from bot
        logger.info("Sent 'bot started' message from bot")

        # Run client until disconnected
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

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_clients())
