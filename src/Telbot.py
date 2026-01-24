import logging
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
import asyncio
from src.Config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID
from src.Config import ConfigManager, validate_env_file
from src.Logger import setup_logging
from src.Handlers import MessageHandler, CallbackHandler, CommandHandler, AccountHandler
from src.Client import SessionManager
from src.Monitor import Monitor

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
            self.tbot = None
            self.active_clients = {}
            self.active_clients_lock = None
            self.handlers = {}
            self._conversations = {}
            self._conversations_lock = None
            self.client_manager = None
            self.account_handler = None
            self.monitor = None

            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.critical(f"Error during bot initialization: {e}")
            raise

    async def start(self):
        """
        Start the bot and initialize all components.
        """
        try:
            # Validate environment configuration before starting
            try:
                validate_env_file()
            except ValueError as e:
                logger.critical(f"Environment configuration error: {e}")
                raise SystemExit(str(e))
            
            # Create TelegramClient now that we're in an async context
            if self.tbot is None:
                self.tbot = TelegramClient('bot2', API_ID, API_HASH)
                logger.info("TelegramClient created")
            
            # Initialize async components now that we're in an async context
            if self.active_clients_lock is None:
                self.active_clients_lock = asyncio.Lock()
            if self._conversations_lock is None:
                self._conversations_lock = asyncio.Lock()
            
            # Initialize managers now that we have locks and client
            if self.client_manager is None:
                self.client_manager = SessionManager(self.config, self.active_clients, self.tbot)
            if self.account_handler is None:
                self.account_handler = AccountHandler(self)
            if self.monitor is None:
                self.monitor = Monitor(self)
            
            logger.info("Starting bot connection...")
            try:
                await self.tbot.start(bot_token=BOT_TOKEN)
                logger.info("Bot connected to Telegram")
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"FloodWaitError: Telegram requires waiting {wait_time} seconds ({wait_time/60:.1f} minutes) before bot can start.")
                logger.info(f"Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                logger.info("Retrying bot connection...")
                await self.tbot.start(bot_token=BOT_TOKEN)
                logger.info("Bot connected to Telegram after waiting")
            
            await self.init_handlers()
            logger.info("Handlers initialized")
            
            await self.client_manager.start_saved_clients()
            logger.info("Saved clients started")
            
            try:
                await self.notify_admin("Bot started successfully and all clients have been detected. Use /start to begin.")
                logger.info("Admin notification sent")
            except Exception as e:
                logger.warning(f"Failed to send admin notification: {e}")
            
            logger.info("Bot started successfully")
        except Exception as e:
            logger.error(f"Error during bot start: {e}", exc_info=True)
            raise

    async def init_handlers(self):
        """
        Initialize all event handlers for the bot.
        """
        try:
            # Register command handler first (with pattern) - this will catch /start before generic handler
            command_handler = CommandHandler(self)
            self.tbot.add_event_handler(
                self.admin_only(command_handler.start_command), 
                events.NewMessage(pattern='^/start$')
            )
            logger.info("Registered /start command handler")
            
            # Register callback handler for button clicks
            callback_handler = CallbackHandler(self)
            self.tbot.add_event_handler(
                callback_handler.callback_handler,
                events.CallbackQuery()
            )
            logger.info("Registered callback query handler")

            # Register generic message handler last (for conversation states)
            # This should NOT catch /start because it's already handled above
            message_handler = MessageHandler(self)
            self.tbot.add_event_handler(
                message_handler.message_handler,
                events.NewMessage()
            )
            logger.info("Registered generic message handler")
            
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
            try:
                sender_id = event.sender_id
                logger.debug(f"admin_only check: sender_id={sender_id}, ADMIN_ID={ADMIN_ID}")
                if sender_id == int(ADMIN_ID):
                    await handler(event)
                else:
                    logger.warning(f"Unauthorized access attempt from user {sender_id}")
                    await event.respond("You are not the admin")
            except Exception as e:
                logger.error(f"Error in admin_only wrapper: {e}", exc_info=True)
                try:
                    await event.respond("An error occurred. Please try again.")
                except (Exception, AttributeError):
                    pass
        return wrapper

    async def run(self):
        """
        Run the bot and monitor clients.
        """
        try:
            await self.start()
            logger.info("Bot is running...")
            logger.info("=" * 60)
            logger.info("✅ Bot started successfully and is ready to receive commands!")
            logger.info("=" * 60)

            # Start monitoring messages for all active clients (only once per client)
            tasks = []
            async with self.active_clients_lock:
                for client in self.active_clients.values():
                    if not hasattr(client, '_message_processing_set'):
                        # Start monitoring tasks in background (don't await them)
                        asyncio.create_task(self.monitor.process_messages_for_client(client))
                        client._message_processing_set = True
            
            # Keep the bot running until disconnected
            logger.info("Bot is now running and waiting for messages...")
            logger.info("Send /start to your bot in Telegram to begin.")
            await self.tbot.run_until_disconnected()
        except asyncio.CancelledError:
            logger.warning("Bot run was cancelled")
        except Exception as e:
            logger.error(f"Error running bot: {e}", exc_info=True)
            try:
                await self.notify_admin(f"❌ Bot encountered an error: {str(e)[:200]}")
            except Exception:
                logger.error("Failed to notify admin about error")
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
