import logging
from telethon import TelegramClient, events, Button
from telethon.utils import get_peer_id
from src.Config import CHANNEL_ID
from src.Keyboards import Keyboard
from src.utils import extract_account_name, get_session_name
from src.Validation import InputValidator
from src.constants import TELEGRAM_MAX_MESSAGE_LENGTH

# Set up logger for the Monitor class
logger = logging.getLogger(__name__)

class Monitor:
    """
    Handles message monitoring and forwarding based on configured keywords.
    
    Monitors messages from all active Telegram accounts and forwards messages
    containing configured keywords to a designated channel.
    """
    
    def __init__(self, tbot):
        """
        Initialize the Monitor class.
        
        Args:
            tbot: Main bot instance containing configuration and Telegram client
        """
        self.tbot = tbot
        self.channel_id = None  # Numeric channel ID
        self.channel_username = None  # Channel username (if applicable)

    async def resolve_channel_id(self) -> None:
        """
        Resolve CHANNEL_ID to numeric ID if it's a username.
        
        Ensures compatibility between username-based and ID-based channel
        references. Caches the resolved ID for subsequent use.
        """
        if self.channel_id is not None:
            return  # Channel ID already resolved

        # Check if CHANNEL_ID is set and valid
        if not CHANNEL_ID or CHANNEL_ID in ['x', 'your_channel_id_or_username', '0']:
            logger.warning("CHANNEL_ID is not configured. Message forwarding will be disabled.")
            return

        # Numeric IDs (including the -100... supergroup/channel form) parse via int().
        # Anything else is treated as a username and resolved to a peer ID.
        try:
            self.channel_id = int(CHANNEL_ID)
            logger.info(f"Using numeric channel ID '{self.channel_id}'")
        except (TypeError, ValueError):
            try:
                # Resolve username to a normalized peer ID (-100... form for channels)
                entity = await self.tbot.tbot.get_entity(CHANNEL_ID)
                self.channel_id = get_peer_id(entity)
                self.channel_username = getattr(entity, 'username', None)
                logger.info(f"Resolved channel username '{CHANNEL_ID}' to ID '{self.channel_id}'")
            except Exception as e:
                logger.error(f"Error resolving channel username '{CHANNEL_ID}': {e}")
                raise

    @staticmethod
    def _sender_info(sender) -> str:
        if not sender:
            return "User: -\n• User ID: -\n"
        first_name = InputValidator.sanitize_input(getattr(sender, 'first_name', '') or '', max_length=50)
        last_name = InputValidator.sanitize_input(getattr(sender, 'last_name', '') or '', max_length=50)
        return f"User: {first_name} {last_name}\n• User ID: {getattr(sender, 'id', 0)}\n"

    @staticmethod
    def _message_link(chat, event) -> str:
        if getattr(chat, 'username', None):
            return f"https://t.me/{chat.username}/{event.id}"
        # Private channels use t.me/c/<id>/<msg> with the -100 prefix stripped.
        chat_id_str = str(event.chat_id)
        if chat_id_str.startswith('-100'):
            chat_id_str = chat_id_str[4:]
        return f"https://t.me/c/{chat_id_str.lstrip('-')}/{event.id}"

    @staticmethod
    def _matches_keywords(message: str, keywords) -> bool:
        return any(keyword.lower() in message.lower() for keyword in keywords)

    async def process_messages_for_client(self, client):
        """
        Set up message processing and forwarding for a specific Telegram client.

        :param client: TelegramClient instance to handle message events for.
        """
        logger.info("Setting up message processing for client.")
        await self.resolve_channel_id()

        if self.channel_id is None:
            logger.warning("CHANNEL_ID not configured. Message forwarding is disabled.")
            return

        # Captured so the closure does not reach back through self.
        channel_id = self.channel_id
        tbot_instance = self.tbot.tbot
        config = self.tbot.config

        async def process_message(event):
            """
            Handle and process new messages received by the client.

            :param event: NewMessage event from Telethon.
            """
            text = None
            try:
                if event.chat_id == channel_id or event.out:
                    logger.debug("Message sent to the channel itself or by the bot. Ignoring to avoid loops.")
                    return

                message = InputValidator.sanitize_input(
                    event.message.text or "-",
                    max_length=TELEGRAM_MAX_MESSAGE_LENGTH - 100
                )
                sender = await event.get_sender()

                if sender and sender.id in config['IGNORE_USERS']:
                    logger.info(f"Message from ignored user {sender.id}. Skipping.")
                    return

                if not self._matches_keywords(message, config['KEYWORDS']):
                    logger.debug("Message does not contain any configured keywords. Skipping.")
                    return

                chat = await event.get_chat()
                chat_title = InputValidator.sanitize_input(
                    getattr(chat, 'title', '') or '', max_length=100) or '-'
                logger.info(f"Processing message from chat: {chat_title}")

                text = (
                    f"Account: {extract_account_name(client)}\n"
                    f"{self._sender_info(sender)}"
                    f"• Chat: {chat_title}\n\n"
                    f"• Message:\n{message}\n"
                )
                buttons = Keyboard.channel_message_keyboard(
                    self._message_link(chat, event), sender.id if sender else 0)

                # parse_mode=None sends user-controlled text literally, so a stray
                # '*' or backtick cannot break parsing and drop the forward.
                await tbot_instance.send_message(
                    channel_id, text, buttons=buttons,
                    link_preview=False, parse_mode=None
                )
                logger.info(f"Forwarded message from user {getattr(sender, 'id', '-') if sender else '-'} in chat {chat_title}.")

            except UnicodeEncodeError as e:
                logger.error(f"UnicodeEncodeError: {e}")
                logger.error(f"Failed text: {text}")
                try:
                    await tbot_instance.send_message(
                        channel_id,
                        "Error processing message due to encoding issues.",
                        link_preview=False
                    )
                except Exception as send_err:
                    logger.error(f"Failed to send encoding error notification: {send_err}")
            except Exception:
                logger.error("Error processing message.", exc_info=True)

        handler = client.on(events.NewMessage)(process_message)

        if not hasattr(client, '_registered_handlers'):
            client._registered_handlers = []
        client._registered_handlers.append(handler)

        logger.info(f"Message processing handler registered for client {get_session_name(client)}")

        return process_message
    
    def cleanup_client_handlers(self, client):
        """
        Remove all event handlers for a client to prevent memory leaks.
        
        :param client: TelegramClient instance to clean up handlers for.
        """
        try:
            if hasattr(client, '_registered_handlers'):
                for handler in client._registered_handlers:
                    try:
                        client.remove_event_handler(handler)
                    except Exception as e:
                        logger.warning(f"Error removing event handler: {e}")
                client._registered_handlers.clear()
                logger.info(f"Cleaned up handlers for client {get_session_name(client)}")
        except Exception as e:
            logger.error(f"Error during handler cleanup: {e}")
