#clinet_manager.py
from telethon import TelegramClient
from telethon import events, Button
import logging
from config import CHANNEL_ID
from telethon import TelegramClient
from telethon import events
import logging
from handlers.account_handler import AccountHandler

logger = logging.getLogger(__name__)

class ClientManager:
    def __init__(self, config, active_clients, api_id, api_hash):
        self.config = config
        self.active_clients = active_clients
        self.api_id = api_id
        self.api_hash = api_hash

    async def start_saved_clients(self):
        """Start all saved client sessions"""
        print("start_saved_clients in ClientManager")
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
        print("disconnect_all_clients in ClientManager")
        for client in self.active_clients.values():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {e}")