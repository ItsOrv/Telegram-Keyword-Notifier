import logging
from telethon import TelegramClient, events, Button
from src.Config import CHANNEL_ID
from src.Keyboards import Keyboard

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
        
        # Check if channel ID is configured
        if self.channel_id is None:
            logger.warning("CHANNEL_ID not configured. Message forwarding is disabled.")
            return
        
        # Capture self references to avoid scope issues in nested function
        channel_id = self.channel_id
        tbot_instance = self.tbot.tbot
        config = self.tbot.config

        # Define the handler function BEFORE decorating to enable cleanup
        async def process_message(event):
            """
            Handle and process new messages received by the client.

            :param event: NewMessage event from Telethon.
            """
            try:
                logger.debug("Received new message event.")

                # Ignore messages sent to the monitored channel or by the bot itself
                if event.chat_id == channel_id or event.out:
                    logger.debug("Message sent to the channel itself or by the bot. Ignoring to avoid loops.")
                    return

                # Extract message text or set a placeholder if empty
                raw_message = event.message.text or "-"
                # Sanitize message text to prevent injection attacks
                from src.Validation import InputValidator
                message = InputValidator.sanitize_input(raw_message, max_length=4000)
                sender = await event.get_sender()
                if sender:
                    # Safely extract and sanitize sender info
                    first_name = InputValidator.sanitize_input(getattr(sender, 'first_name', '') or '', max_length=50)
                    last_name = InputValidator.sanitize_input(getattr(sender, 'last_name', '') or '', max_length=50)
                    sender_id = getattr(sender, 'id', 0)
                    sender_info = f"User: {first_name} {last_name}\n• User ID: `{sender_id}`\n"
                else:
                    sender_info = "User: -\n• User ID: -\n"

                # Ignore messages from users listed in the IGNORE_USERS configuration
                if sender and sender.id in config['IGNORE_USERS']:
                    logger.info(f"Message from ignored user {sender.id}. Skipping.")
                    return

                # Check if the message contains any of the configured keywords
                if not any(keyword.lower() in message.lower() for keyword in config['KEYWORDS']):
                    logger.debug("Message does not contain any configured keywords. Skipping.")
                    return

                # Extract chat information
                chat = await event.get_chat()
                raw_chat_title = getattr(chat, 'title', '') or ''
                chat_title = InputValidator.sanitize_input(raw_chat_title, max_length=100) or '-'
                logger.info(f"Processing message from chat: {chat_title}")

                # Extract session name from the client's session file
                try:
                    if hasattr(client.session, 'filename'):
                        account_name = str(client.session.filename)
                        # Remove .session extension if present
                        if account_name.endswith('.session'):
                            account_name = account_name[:-8]
                    else:
                        account_name = 'Unknown Account'
                except Exception as e:
                    logger.warning(f"Could not extract account name: {e}")
                    account_name = 'Unknown Account'

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
                await tbot_instance.send_message(
                    channel_id,
                    text,
                    buttons=buttons,
                    link_preview=False
                )

                logger.info(f"Forwarded message from user {getattr(sender, 'id', '-') if sender else '-'} in chat {chat_title}.")

            except UnicodeEncodeError as e:
                # Handle encoding errors gracefully
                logger.error(f"UnicodeEncodeError: {e}")
                logger.error(f"Failed text: {text}")
                await tbot_instance.send_message(
                    channel_id,
                    "Error processing message due to encoding issues.",
                    link_preview=False
                )
            except Exception as e:
                # Handle any unexpected errors during message processing
                logger.error("Error processing message.", exc_info=True)
        
        # Register the event handler
        handler = client.on(events.NewMessage)(process_message)
        
        # Store handler reference for cleanup
        if not hasattr(client, '_registered_handlers'):
            client._registered_handlers = []
        client._registered_handlers.append(handler)
        
        logger.info(f"Message processing handler registered for client {client.session.filename if hasattr(client, 'session') else 'Unknown'}")
    
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
                logger.info(f"Cleaned up handlers for client {client.session.filename if hasattr(client, 'session') else 'Unknown'}")
        except Exception as e:
            logger.error(f"Error during handler cleanup: {e}")
