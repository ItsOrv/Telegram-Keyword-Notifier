import logging
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import User, Channel, Chat
from config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID
import asyncio
import json
import os
from typing import Dict, List, Union
from datetime import datetime
from utils.config_manager import ConfigManager
from utils.logging_setup import setup_logging
from handlers.message_handler import MessageHandler
from handlers.callback_handler import CallbackHandler
from handlers.command_handler import CommandHandler
from handlers.account_handler import AccountHandler
from handlers.keyword_handler import KeywordHandler
from handlers.stats_handler import StatsHandler
from clients.client_manager import ClientManager

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.config_manager = ConfigManager('clients.json')
        self.bot = TelegramClient('bot2', API_ID, API_HASH)
        self.active_clients: Dict[str, TelegramClient] = {}
        self.config = self.config_manager.load_config()
        self.handlers = {}  # Store message handlers
        self.conversations = {}  # Store active conversations
        self.client_manager = ClientManager(self.config, self.active_clients, API_ID, API_HASH)

    async def init_handlers(self):
        """Initialize all event handlers"""
        self.bot.add_event_handler(CommandHandler(self.bot).start_command, events.NewMessage(pattern='/start'))
        self.bot.add_event_handler(CallbackHandler(self.bot).callback_handler, events.CallbackQuery())
        self.bot.add_event_handler(MessageHandler(self.bot).message_handler, events.NewMessage())

    async def start(self):
        """Start the bot and initialize all components"""
        await self.bot.start(bot_token=BOT_TOKEN)
        await self.init_handlers()
        await self.client_manager.start_saved_clients()
        logger.info("Bot started successfully")

    async def run(self):
        """Run the bot"""
        try:
            await self.start()
            logger.info("Bot is running...")
            await self.bot.run_until_disconnected()
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            # Cleanup
            await self.client_manager.disconnect_all_clients()
            await self.bot.disconnect()

# Corrected main function to use asyncio.run()
async def main():
    setup_logging()  # Set up logging configuration
    bot = TelegramBot()  # Create an instance of TelegramBot
    await bot.run()  # Run the bot

# Ensure the script runs properly using asyncio
if __name__ == '__main__':
    asyncio.run(main())
