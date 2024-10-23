from telethon import TelegramClient
from telethon import events, Button
from telethon.tl.types import User, Channel, Chat
import logging
from config import API_ID, API_HASH, BOT_TOKEN, TARGET_GROUPS, KEYWORDS, CHANNEL_ID, IGNORE_USERS, load_json_config, update_json_config

logger = logging.getLogger(__name__)

class ClientManager:
    def __init__(self, config, active_clients, api_id, api_hash):
        self.config = config
        self.active_clients = active_clients
        self.api_id = api_id
        self.api_hash = api_hash

    async def start_saved_clients(self):
        """Start all saved client sessions"""
        for client_info in self.config['clients']:
            session_name = client_info['session']
            if not client_info.get('disabled', False):  # Only start enabled clients
                try:
                    client = TelegramClient(session_name, self.api_id, self.api_hash)
                    await client.start()
                    self.active_clients[session_name] = client
                    # Add message handler for this client
                    client.add_event_handler(
                        self.process_message,
                        events.NewMessage(chats=client_info.get('groups', []))
                    )
                    logger.info(f"Started client: {session_name}")
                except Exception as e:
                    logger.error(f"Error starting client {session_name}: {e}")

    async def disconnect_all_clients(self):
        """Disconnect all active clients"""
        for client in self.active_clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")

    async def process_message(self, event):
        """Process and forward messages"""
        try:
            message = event.message.text
            if not message:
                return

            sender = await event.get_sender()
            if not sender or sender.id in self.config['IGNORE_USERS']:
                return

            # Check keywords
            if not any(keyword.lower() in message.lower() for keyword in self.config['KEYWORDS']):
                return

            # Get chat info
            chat = await event.get_chat()
            chat_title = getattr(chat, 'title', 'Unknown Chat')

            # Format message
            text = (
                f"📝 New Message\n\n"
                f"👤 From: {getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}\n"
                f"🆔 User ID: `{sender.id}`\n"
                f"💭 Chat: {chat_title}\n\n"
                f"📜 Message:\n{message}\n"
            )

            # Get message link
            if hasattr(chat, 'username') and chat.username:
                message_link = f"https://t.me/{chat.username}/{event.id}"
            else:
                chat_id = str(event.chat_id).replace('-100', '', 1)
                message_link = f"https://t.me/c/{chat_id}/{event.id}"

            buttons = [[Button.url("📎 View Message", url=message_link)]]

            await self.bot.send_message(
                CHANNEL_ID,
                text,
                buttons=buttons,
                link_preview=False
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
