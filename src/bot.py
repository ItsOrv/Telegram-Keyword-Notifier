import logging
from telethon import TelegramClient, events, Button
from config import API_ID, API_HASH, BOT_TOKEN
import asyncio
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
        self.active_clients = {}
        self.config = self.config_manager.load_config()
        self.handlers = {}
        self._conversations = {}
        self.client_manager = ClientManager(self.config, self.active_clients, API_ID, API_HASH)
        self.account_handler = AccountHandler(self)

    async def start(self):
        """Start the bot and initialize all components"""
        await self.bot.start(bot_token=BOT_TOKEN)
        await self.init_handlers()
        await self.client_manager.start_saved_clients()
        logger.info("Bot started successfully")

    async def init_handlers(self):
        """Initialize all event handlers"""
        self.bot.add_event_handler(CommandHandler(self).start_command, events.NewMessage(pattern='/start'))
        self.bot.add_event_handler(CallbackHandler(self).callback_handler, events.CallbackQuery())
        self.bot.add_event_handler(MessageHandler(self).message_handler, events.NewMessage())


    async def run(self):
        """Run the bot"""
        try:
            await self.start()
            logger.info("Bot is running...")

            tasks = [self.account_handler.process_messages_for_client(client) for client in self.active_clients.values()]
            await asyncio.gather(*tasks)

            await self.bot.run_until_disconnected()
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            await self.client_manager.disconnect_all_clients()
            await self.bot.disconnect()
