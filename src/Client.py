import os
import logging
import asyncio
from telethon import TelegramClient
from src.Config import ConfigManager, API_ID, API_HASH, PORTS

# Set up logger for the ClientManager class
logger = logging.getLogger(__name__)

class ClientManager:
    def __init__(self, config, active_clients):
        """
        Initialize the ClientManager to handle Telegram client sessions.
        :param config: Configuration dictionary for client sessions.
        :param active_clients: Dictionary of active clients mapped by session names.
        """
        try:
            self.config = config
            self.active_clients = active_clients
            # Use ConfigManager to manage client configurations
            self.config_manager = ConfigManager("clients.json", self.config)
            logger.info("ClientManager initialized successfully.")
        except Exception as e:
            logger.critical(f"Error initializing ClientManager: {e}")
            raise

    def detect_sessions(self):
        """
        Detect and load Telegram client sessions from the configuration.
        Adds sessions to `active_clients` if they are not already active.
        """
        try:
            if not isinstance(self.config.get('clients', {}), dict):
                logger.warning("'clients' is not a dictionary. Initializing it as an empty dictionary.")
                self.config['clients'] = {}

            for session_name in self.config['clients']:
                if session_name not in self.active_clients:
                    # Initialize Telegram client for the session with the configured port
                    client = TelegramClient(session_name, API_ID, API_HASH)
                    self.active_clients[session_name] = client
            logger.info("Sessions detected and loaded successfully.")
        except Exception as e:
            logger.error(f"Error detecting sessions: {e}")

    async def start_saved_clients(self):
        """
        Start all Telegram client sessions listed in the configuration.
        Ensures clients are authorized and ready to use.
        """
        try:
            # Load session information into active_clients
            self.detect_sessions()

            for session_name, client in self.active_clients.items():
                try:
                    # Connect client if not already connected
                    if not client.is_connected():
                        await client.connect()

                    # Check if the client is authorized
                    if await client.is_user_authorized():
                        logger.info(f"Started client: {session_name}")
                    else:
                        logger.warning(f"Client {session_name} is not authorized. Disconnecting...")
                        await client.disconnect()

                    # Sleep to avoid hitting Telegram flood limits
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.error(f"Error starting client {session_name}: {e}")
        except Exception as e:
            logger.error(f"Error in start_saved_clients: {e}")

    async def disconnect_all_clients(self):
        """
        Disconnect all active Telegram clients and clear the active client list.
        """
        try:
            for session_name, client in self.active_clients.items():
                try:
                    await client.disconnect()
                    logger.info(f"Client {session_name} disconnected successfully.")
                except Exception as e:
                    logger.error(f"Error disconnecting client {session_name}: {e}")
            
            # Clear the active_clients dictionary
            self.active_clients.clear()
            logger.info("All clients disconnected successfully.")
        except Exception as e:
            logger.error(f"Error disconnecting clients: {e}")
