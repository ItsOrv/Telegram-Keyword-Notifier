import logging
from telethon import TelegramClient, events, Button
from src.Config import CHANNEL_ID
from src.Handlers import Keyboard  # Add this import

logger = logging.getLogger(__name__)

class Monitor:
    def __init__(self, tbot):
        self.tbot = tbot
        self.channel_id = None
        self.channel_username = None

    async def resolve_channel_id(self):
        """
        Resolve the CHANNEL_ID to a numeric ID if it's a username.
        """
        if isinstance(CHANNEL_ID, str) and not CHANNEL_ID.isdigit():
            try:
                entity = await self.tbot.tbot.get_entity(CHANNEL_ID)
                self.channel_id = entity.id
                self.channel_username = entity.username
                logger.info(f"Resolved channel username '{CHANNEL_ID}' to ID '{self.channel_id}'")
            except Exception as e:
                logger.error(f"Error resolving channel username '{CHANNEL_ID}': {e}")
                raise
        else:
            self.channel_id = int(CHANNEL_ID)
            logger.info(f"Using numeric channel ID '{self.channel_id}'")

    async def process_messages_for_client(self, client):
        """
        Sets up message processing for a specific client.

        Args:
            client: TelegramClient instance to process messages for
        """
        logger.info("Setting up message processing for client.")
        await self.resolve_channel_id()

        @client.on(events.NewMessage)
        async def process_message(event):
            """
            Processes and forwards new messages based on configured filters.

            Args:
                event: NewMessage event from Telegram
            """
            try:
                logger.debug("Received new message event.")

                # Ignore messages sent to the channel to avoid loops
                if event.chat_id == self.channel_id or event.out:
                    logger.debug("Message sent to the channel itself or by the bot. Ignoring to avoid loops.")
                    return

                message = event.message.text
                if not message:
                    logger.debug("Message text is empty. Skipping.")
                    return

                sender = await event.get_sender()
                if not sender:
                    logger.warning("Could not fetch sender information. Skipping message.")
                    return

                if sender.id in self.tbot.config['IGNORE_USERS']:
                    logger.info(f"Message from ignored user {sender.id}. Skipping.")
                    return

                if not any(keyword.lower() in message.lower() for keyword in self.tbot.config['KEYWORDS']):
                    logger.debug("Message does not contain any configured keywords. Skipping.")
                    return

                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', 'Unknown Chat')

                # Check if the message is from the same username as the channel
                if hasattr(chat, 'username') and chat.username == self.channel_username:
                    logger.debug("Message from the same username as the channel. Ignoring to avoid loops.")
                    return

                logger.info(f"Processing message from chat: {chat_title}")

                text = (
                    f"• User: {getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}\n"
                    f"• User ID: `{sender.id}`\n"
                    f"• Chat: {chat_title}\n\n"
                    f"• Message:\n{message}\n"
                )

                if hasattr(chat, 'username') and chat.username:
                    message_link = f"https://t.me/{chat.username}/{event.id}"
                else:
                    chat_id = str(event.chat_id).replace('-100', '', 1).replace('-', '')
                    message_link = f"https://t.me/c/{chat_id}/{event.id}"

                buttons = Keyboard.channel_message_keyboard(message_link, sender.id)

                logger.debug(f"Sending message: {text}")
                logger.debug(f"Buttons: {buttons}")

                await self.tbot.tbot.send_message(
                    self.channel_id,
                    text,
                    buttons=buttons,
                    link_preview=False
                )

                logger.info(f"Forwarded message from user {sender.id} in chat {chat_title}.")

            except UnicodeEncodeError as e:
                logger.error(f"UnicodeEncodeError: {e}")
                logger.error(f"Failed text: {text}")
                await self.tbot.tbot.send_message(
                    self.channel_id,
                    "Error processing message due to encoding issues.",
                    link_preview=False
                )
            except Exception as e:
                logger.error("Error processing message.", exc_info=True)