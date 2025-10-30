import logging
from telethon import TelegramClient, events, Button
import asyncio
from src.Config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, PORTS
from src.Config import ConfigManager
from src.Logger import setup_logging
from src.Handlers import MessageHandler, CallbackHandler, CommandHandler, AccountHandler
from src.Client import SessionManager
from src.Monitor import Monitor

# تنظیم لاگینگ
setup_logging()
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        """
        Initialize the TelegramBot class with necessary components.
        """
        try:
            self.config_manager = ConfigManager('clients.json')
            self.config = self.config_manager.load_config()
            self.tbot = TelegramClient('bot2', API_ID, API_HASH)
            self.active_clients = {}
            self.active_clients_lock = asyncio.Lock()  # Protection against race conditions
            self.handlers = {}
            self._conversations = {}
            self.client_manager = SessionManager(self.config, self.active_clients, self.tbot)
            self.account_handler = AccountHandler(self)
            self.monitor = Monitor(self)

            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.critical(f"Error during bot initialization: {e}")
            raise

    async def start(self):
        """
        Start the bot and initialize all components.
        """
        try:
            await self.tbot.start(bot_token=BOT_TOKEN)
            await self.init_handlers()
            await self.client_manager.start_saved_clients()
            await self.notify_admin("Bot started successfully and all clients have been detected. Use /start to begin.")
            logger.info("Bot started successfully")
        except Exception as e:
            logger.error(f"Error during bot start: {e}")
            raise

    async def init_handlers(self):
        """
        Initialize all event handlers for the bot.
        """
        try:
            self.tbot.add_event_handler(self.admin_only(CommandHandler(self).start_command), events.NewMessage(pattern='/start'))
            self.tbot.add_event_handler(self.admin_only(CallbackHandler(self).callback_handler), events.CallbackQuery())
            self.tbot.add_event_handler(self.admin_only(MessageHandler(self).message_handler), events.NewMessage())
            logger.info("Handlers initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing handlers: {e}")
            raise

    def admin_only(self, handler):
        """
        Decorator to restrict access to admin-only handlers.

        :param handler: The handler function to wrap.
        """
        async def wrapper(event):
            if event.sender_id == int(ADMIN_ID):
                await handler(event)
            else:
                await event.respond("You are not the admin")
        return wrapper

    async def run(self):
        """
        Run the bot and monitor clients.
        """
        try:
            await self.start()
            logger.info("Bot is running...")

            # Start monitoring messages for all active clients (only once per client)
            tasks = []
            async with self.active_clients_lock:
                for client in self.active_clients.values():
                    if not hasattr(client, '_message_processing_set'):
                        tasks.append(self.monitor.process_messages_for_client(client))
                        client._message_processing_set = True

            # Use return_exceptions to prevent one failed task from cancelling others
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {i} failed with error: {result}")
            
            await self.tbot.run_until_disconnected()
        except asyncio.CancelledError:
            logger.warning("Bot run was cancelled")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            await self.shutdown()

    async def notify_admin(self, message):
        """
        Send a notification message to the admin.

        :param message: The message text to send.
        """
        try:
            admin_id = int(ADMIN_ID)  # Ensure ADMIN_ID is an integer
            await self.tbot.send_message(admin_id, message)
            logger.info("Notification sent to admin.")
        except Exception as e:
            logger.error(f"Error sending notification to admin: {e}")

    async def shutdown(self):
        """
        Clean up resources and shut down the bot gracefully.
        """
        try:
            logger.info("Shutting down bot...")
            await self.client_manager.disconnect_all_clients()
            await self.tbot.disconnect()
            logger.info("Bot shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
