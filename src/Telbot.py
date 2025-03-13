import logging
from telethon import TelegramClient, events, Button
from src.Config import API_ID, API_HASH, BOT_TOKEN
import asyncio
from src.Config import ConfigManager
from src.Logger import setup_logging
from src.Handlers import MessageHandler
from src.Handlers import CallbackHandler
from src.Handlers import CommandHandler
from src.Handlers import AccountHandler
from src.Client import ClientManager


# تنظیم لاگینگ
setup_logging()
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        try:
            self.config_manager = ConfigManager('clients.json')
            self.tbot = TelegramClient('bot2', API_ID, API_HASH)
            self.active_clients = {}
            self.config = self.config_manager.load_config()
            self.handlers = {}
            self._conversations = {}
            self.client_manager = ClientManager(self.config, self.active_clients)
            self.account_handler = AccountHandler(self)
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.critical(f"Error during bot initialization: {e}")
            raise

    async def start(self):
        """Start the bot and initialize all components"""
        try:
            await self.tbot.start(bot_token=BOT_TOKEN)
            await self.init_handlers()
            await self.client_manager.start_saved_clients()
            logger.info("Bot started successfully")
        except Exception as e:
            logger.error(f"Error during bot start: {e}")
            raise

    async def init_handlers(self):
        """Initialize all event handlers"""
        try:
            self.tbot.add_event_handler(CommandHandler(self).start_command, events.NewMessage(pattern='/start'))
            self.tbot.add_event_handler(CallbackHandler(self).callback_handler, events.CallbackQuery())
            self.tbot.add_event_handler(MessageHandler(self).message_handler, events.NewMessage())
            logger.info("Handlers initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing handlers: {e}")
            raise

    async def run(self):
        """Run the bot"""
        try:
            await self.start()
            logger.info("Bot is running...")

            tasks = [self.account_handler.process_message(client) for client in self.active_clients.values()]
            await asyncio.gather(*tasks)

            await self.tbot.run_until_disconnected()
        except asyncio.CancelledError:
            logger.warning("Bot run was cancelled")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Clean up resources during shutdown"""
        try:
            logger.info("Shutting down bot...")
            await self.client_manager.disconnect_all_clients()
            await self.tbot.disconnect()
            logger.info("Bot shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
