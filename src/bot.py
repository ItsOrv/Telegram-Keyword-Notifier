import logging
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from config import API_ID, API_HASH, BOT_TOKEN, TARGET_GROUPS, KEYWORDS, CHANNEL_ID, SESSION_NAME, IGNORE_USERS
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the clients
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(chats=TARGET_GROUPS))
async def my_event_handler(event):
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

            # Send message to the channel using the bot
            logger.info(f"Attempting to send message to channel: {CHANNEL_ID}")
            try:
                await bot.send_message(CHANNEL_ID, text, link_preview=False)
                logger.info(f"Message forwarded to channel {CHANNEL_ID}")
            except Exception as e:
                logger.error(f"Failed to send message to channel {CHANNEL_ID}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

async def start_clients():
    try:
        # Start both clients
        await client.start()
        logger.info("Client started successfully")
        await bot.start()
        logger.info("Bot started successfully")


        # Send startup messages
        try:
            await client.send_message(CHANNEL_ID, "account started")
            logger.info("Sent 'account started' message from account")
        except Exception as e:
            logger.error(f"Failed to send 'account started' message: {e}", exc_info=True)

        try:
            await bot.send_message(CHANNEL_ID, "bot started")
            logger.info("Sent 'bot started' message from bot")
        except Exception as e:
            logger.error(f"Failed to send 'bot started' message: {e}", exc_info=True)

        # Run client until disconnected
        await client.run_until_disconnected()

    except SessionPasswordNeededError:
        logger.error("2FA enabled. Please provide the second factor.")
    except Exception as e:
        logger.error(f"Error starting the client or bot: {e}", exc_info=True)
    finally:
        await client.disconnect()
        await bot.disconnect()
        logger.info("Client and bot disconnected")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_clients())
