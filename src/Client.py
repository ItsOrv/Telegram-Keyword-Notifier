import os
import logging
import asyncio
from telethon import TelegramClient
from src.Config import ConfigManager
from src.Config import API_ID, API_HASH

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
        """Detect and load sessions from the configuration"""
        try:
            if not isinstance(self.config['clients'], dict):
                logger.warning("'clients' is not a dictionary. Initializing it as an empty dictionary.")
                self.config['clients'] = {}

            for session_name in self.config['clients']:
                if session_name not in self.active_clients:
                    client = TelegramClient(session_name, API_ID, API_HASH)
                    self.active_clients[session_name] = client
            logger.info("Sessions detected and loaded successfully.")
        except Exception as e:
            logger.error(f"Error detecting sessions: {e}")

    async def start_saved_clients(self):
        """Start all clients listed in the configuration."""
        try:
            self.detect_sessions()

            for session_name in self.config.get('clients', {}):
                try:
                    client = self.active_clients.get(session_name)
                    if client is None:
                        client = TelegramClient(session_name, API_ID, API_HASH)
                        self.active_clients[session_name] = client

                    await client.connect()

                    if await client.is_user_authorized():
                        logger.info(f"Started client: {session_name}")
                    else:
                        logger.warning(f"Client {session_name} is not authorized, skipping.")
                        await client.disconnect()

                    await asyncio.sleep(3)  # Increase sleep time to avoid flood wait errors
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
