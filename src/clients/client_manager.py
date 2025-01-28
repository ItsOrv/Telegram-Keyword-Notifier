import os
from telethon import TelegramClient
import logging
from utils.config_manager import ConfigManager
import asyncio

logger = logging.getLogger(__name__)

class ClientManager:
    def __init__(self, config, active_clients, api_id, api_hash):
        self.config = config
        self.active_clients = active_clients
        self.api_id = api_id
        self.api_hash = api_hash
        self.config_manager = ConfigManager("clients.json", self.config)

    #PASS
    def detect_sessions(self):
        """Detects session files and adds them to the config if not already present."""
        sessions = []
        for filename in os.listdir('.'):
            if filename.endswith('.session') and filename != 'bot2.session' and filename not in self.config.get('clients', []):
                sessions.append(filename)

        if sessions:
            if 'clients' not in self.config:
                self.config['clients'] = []
            self.config['clients'].extend(sessions)
            self.config_manager.save_config(self.config)
            logger.info(f"Detected sessions: {sessions}")
        else:
            logger.info("No new sessions detected.")

    #XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    async def start_saved_clients(self):
        """Start all clients listed in the configuration."""
        self.detect_sessions()

        for session_name in self.config.get('clients', []):
            client = TelegramClient(session_name, self.api_id, self.api_hash)
            await client.start()
            if await client.is_user_authorized():
                self.active_clients[session_name] = client
                logger.info(f"Started client: {session_name}")
            else:
                logger.info(f"Client {session_name} is not authorized, skipping.")
                await client.disconnect()
            await asyncio.sleep(1)
    #XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

    #PASS
    async def disconnect_all_clients(self):
        """Disconnect all active clients."""
        for client in self.active_clients.values():
            await client.disconnect()
        self.active_clients.clear()
