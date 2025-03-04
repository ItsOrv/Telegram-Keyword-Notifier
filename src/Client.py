import os
import logging
import asyncio
from telethon import TelegramClient
from src.Config import ConfigManager
from src.Config import API_ID, API_HASH, BOT_TOKEN

logger = logging.getLogger(__name__)

class ClientManager:
    def __init__(self, config, active_clients):
        try:
            self.config = config
            self.active_clients = active_clients
            self.config_manager = ConfigManager("clients.json", self.config)
            logger.info("ClientManager initialized successfully.")
        except Exception as e:
            logger.critical(f"Error initializing ClientManager: {e}")
            raise

    def detect_sessions(self):
        """Detect session files and add them to the config if not already present."""
        try:
            sessions = []
            for filename in os.listdir('.'):
                if filename.endswith('.session') and filename != 'bot2.session' and filename not in self.config.get('clients', []):
                    sessions.append(filename)

            if sessions:
                self.config.setdefault('clients', []).extend(sessions)
                self.config_manager.save_config(self.config)
                logger.info(f"Detected sessions: {sessions}")
            else:
                logger.info("No new sessions detected.")
        except Exception as e:
            logger.error(f"Error detecting sessions: {e}")

    async def start_saved_clients(self):
        """Start all clients listed in the configuration."""
        try:
            self.detect_sessions()

            for session_name in self.config.get('clients', []):
                try:
                    client = TelegramClient(session_name, API_ID, API_HASH)
                    await client.start()

                    if await client.is_user_authorized():
                        self.active_clients[session_name] = client
                        logger.info(f"Started client: {session_name}")
                    else:
                        logger.warning(f"Client {session_name} is not authorized, skipping.")
                        await client.disconnect()

                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error starting client {session_name}: {e}")
        except Exception as e:
            logger.error(f"Error in start_saved_clients: {e}")

    async def disconnect_all_clients(self):
        """Disconnect all active clients."""
        try:
            for client in self.active_clients.values():
                await client.disconnect()
            self.active_clients.clear()
            logger.info("All clients disconnected successfully.")
        except Exception as e:
            logger.error(f"Error disconnecting clients: {e}")
