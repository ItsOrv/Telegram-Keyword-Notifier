# bot.py
import logging
from telethon import TelegramClient, events
from telethon.tl.types import InputMessageID
from telethon.errors import SessionPasswordNeededError
from config import API_ID, API_HASH, BOT_TOKEN, TARGET_GROUPS, KEYWORDS, CHANNEL_ID, SESSION_NAME, IGNORE_USERS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(chats=TARGET_GROUPS))
async def my_event_handler(event):
    message = event.message.message
    try:
        user = await event.message.get_sender()
        user_id = user.id

        if user_id in IGNORE_USERS:
            logger.info(f"Message ignored from user: {user_id}")
            return

        if any(keyword in message for keyword in KEYWORDS):
            user_username = user.username if user.username else str(user.id)

            if event.chat.username:
                message_link = f"https://t.me/{event.chat.username}/{event.id}"
            else:
                msg = await client.get_messages(event.chat_id, ids=InputMessageID(id=event.id))
                chat_id = str(event.chat_id)
                if chat_id.startswith('-100'):
                    chat_id = chat_id[4:]
                message_link = f"https://t.me/c/{chat_id}/{msg.id}"

            text = (f"• Text:\n{message} \n• ID: @{user_username}\n• Link: {message_link}\n\n")
            await bot.send_message(CHANNEL_ID, text, link_preview=False)
    except Exception as e:
        logger.error(f"Error processing message: {e}")

async def main():
    try:
        await client.start()
        logger.info("Client is running...")
        await client.run_until_disconnected()
    except SessionPasswordNeededError:
        logger.error("2FA enabled. Please provide the second factor.")
    except Exception as e:
        logger.error(f"Error starting the client: {e}")
    finally:
        await client.disconnect()
        logger.info("Client disconnected")

if __name__ == '__main__':
    client.loop.run_until_complete(main())
