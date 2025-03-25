import logging
from telethon import TelegramClient, events, Button
from src.Config import CHANNEL_ID
from src.Handlers import Keyboard

# Set up logger for the Monitor class
logger = logging.getLogger(__name__)

class Monitor:
    def __init__(self, tbot):
        """
        Initialize the Monitor class to handle message monitoring and forwarding.
        
        :param tbot: Main bot instance containing configuration and Telegram client.
        """
        self.tbot = tbot
        self.channel_id = None  # Numeric channel ID
        self.channel_username = None  # Channel username (if applicable)

    async def resolve_channel_id(self):
        """
        Resolve the CHANNEL_ID to a numeric ID if it's a username.
        This ensures compatibility between username-based and ID-based channel references.
        """
        if self.channel_id is not None:
            return  # Channel ID already resolved

        if isinstance(CHANNEL_ID, str) and not CHANNEL_ID.isdigit():
            try:
                # Resolve username to numeric ID
                entity = await self.tbot.tbot.get_entity(CHANNEL_ID)
                self.channel_id = entity.id
                self.channel_username = entity.username
                logger.info(f"Resolved channel username '{CHANNEL_ID}' to ID '{self.channel_id}'")
            except Exception as e:
                logger.error(f"Error resolving channel username '{CHANNEL_ID}': {e}")
                raise
        else:
            # Use numeric ID directly
            self.channel_id = int(CHANNEL_ID)
            logger.info(f"Using numeric channel ID '{self.channel_id}'")

    async def process_messages_for_client(self, client):
        """
        Set up message processing and forwarding for a specific Telegram client.

        :param client: TelegramClient instance to handle message events for.
        """
        logger.info("Setting up message processing for client.")
        await self.resolve_channel_id()  # Ensure channel ID is resolved

        @client.on(events.NewMessage)
        async def process_message(event):
            """
            Handle and process new messages received by the client.

            :param event: NewMessage event from Telethon.
            """
            try:
                logger.debug("Received new message event.")

                # Ignore messages sent to the monitored channel or by the bot itself
                if event.chat_id == self.channel_id or event.out:
                    logger.debug("Message sent to the channel itself or by the bot. Ignoring to avoid loops.")
                    return

                # Extract message text or set a placeholder if empty
                message = event.message.text or "-"
                sender = await event.get_sender()
                sender_info = (
                    f"User: {getattr(sender, 'first_name', '-') or '-'} {getattr(sender, 'last_name', '-') or '-'}\n"
                    f"• User ID: `{getattr(sender, 'id', '-')}`\n"
                    if sender else "User: -\n• User ID: -\n"
                )

                # Ignore messages from users listed in the IGNORE_USERS configuration
                if sender and sender.id in self.tbot.config['IGNORE_USERS']:
                    logger.info(f"Message from ignored user {sender.id}. Skipping.")
                    return

                # Check if the message contains any of the configured keywords
                if not any(keyword.lower() in message.lower() for keyword in self.tbot.config['KEYWORDS']):
                    logger.debug("Message does not contain any configured keywords. Skipping.")
                    return

                # Extract chat information
                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', '-') or '-'
                logger.info(f"Processing message from chat: {chat_title}")

                # Extract session name from the client's session file
                account_name = client.session.filename.replace('.session', '')

                # Prepare the message content for forwarding
                text = (
                    f"Account: {account_name}\n"
                    f"{sender_info}"
                    f"• Chat: {chat_title}\n\n"
                    f"• Message:\n{message}\n"
                )

                # Generate a link to the original message
                if hasattr(chat, 'username') and chat.username:
                    message_link = f"https://t.me/{chat.username}/{event.id}"
                else:
                    chat_id = str(event.chat_id).replace('-100', '', 1).replace('-', '')
                    message_link = f"https://t.me/c/{chat_id}/{event.id}"

                # Create buttons for the forwarded message
                buttons = Keyboard.channel_message_keyboard(message_link, sender.id if sender else 0)

                # Forward the message to the configured channel
                await self.tbot.tbot.send_message(
                    self.channel_id,
                    text,
                    buttons=buttons,
                    link_preview=False
                )

                logger.info(f"Forwarded message from user {getattr(sender, 'id', '-') if sender else '-'} in chat {chat_title}.")

            except UnicodeEncodeError as e:
                # Handle encoding errors gracefully
                logger.error(f"UnicodeEncodeError: {e}")
                logger.error(f"Failed text: {text}")
                await self.tbot.tbot.send_message(
                    self.channel_id,
                    "Error processing message due to encoding issues.",
                    link_preview=False
                )
            except Exception as e:
                # Handle any unexpected errors during message processing
                logger.error("Error processing message.", exc_info=True)
