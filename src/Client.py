import os
import logging
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from src.Config import ConfigManager, API_ID, API_HASH, ADMIN_ID, CHANNEL_ID, CLIENTS_JSON_PATH, RATE_LIMIT_SLEEP, GROUPS_BATCH_SIZE, GROUPS_UPDATE_SLEEP
from src.Keyboards import Keyboard
from src.Validation import InputValidator


# Set up logger for the SessionManager class
logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, config, active_clients, tbot):
        """
        Initialize the SessionManager to handle Telegram client sessions.
        :param config: Configuration dictionary for client sessions.
        :param active_clients: Dictionary of active clients mapped by session names.
        :param tbot: Telegram bot instance for sending messages.
        """
        try:
            self.config = config
            self.active_clients = active_clients
            self.tbot = tbot
            # Use ConfigManager to manage client configurations
            self.config_manager = ConfigManager("clients.json", self.config)
            logger.info("SessionManager initialized successfully.")
        except Exception as e:
            logger.critical(f"Error initializing SessionManager: {e}")
            raise

    async def detect_sessions(self):
        """
        Detect and load Telegram client sessions from the configuration.
        Adds sessions to `active_clients` if they are not already active.
        Note: This method is now async to support proper locking.
        """
        try:
            if not isinstance(self.config.get('clients', {}), dict):
                logger.warning("'clients' is not a dictionary. Initializing it as an empty dictionary.")
                self.config['clients'] = {}

            # If tbot has active_clients_lock, use it for thread-safety
            if hasattr(self.tbot, 'active_clients_lock'):
                async with self.tbot.active_clients_lock:
                    for session_name in list(self.config['clients']):
                        if session_name not in self.active_clients:
                            # Initialize Telegram client for the session
                            client = TelegramClient(session_name, API_ID, API_HASH)
                            self.active_clients[session_name] = client
            else:
                # Fallback if lock is not available (shouldn't happen in production)
                for session_name in list(self.config['clients']):
                    if session_name not in self.active_clients:
                        client = TelegramClient(session_name, API_ID, API_HASH)
                        self.active_clients[session_name] = client
            
            logger.info("Sessions detected and loaded successfully.")
        except Exception as e:
            logger.error(f"Error detecting sessions: {e}")

    async def start_saved_clients(self):
        """
        Start all Telegram client sessions listed in the configuration.
        Ensures clients are authorized and ready to use.

        Account Persistence Behavior:
        - Accounts persist in clients.json and .session files
        - Only true SessionRevokedError sessions are deleted
        - Temporary network/API errors don't delete sessions
        - Accounts remain available for future use
        - Inactive accounts are tracked for admin review
        """
        try:
            # Load session information into active_clients
            await self.detect_sessions()

            # Initialize inactive accounts tracking
            if 'inactive_accounts' not in self.config:
                self.config['inactive_accounts'] = {}

            for session_name, client in list(self.active_clients.items()):
                try:
                    # Connect client if not already connected
                    if not client.is_connected():
                        await client.connect()

                    # Check if the client is authorized
                    if await client.is_user_authorized():
                        logger.info(f"Successfully loaded and authorized client: {session_name}")
                        # Remove from inactive list if it was there
                        if session_name in self.config['inactive_accounts']:
                            del self.config['inactive_accounts'][session_name]
                            self.config_manager.save_config(self.config)
                        # Ensure session is saved after successful authorization
                        client.session.save()
                    else:
                        # Client reported as unauthorized - check if it's really revoked
                        logger.warning(f"Client {session_name} reported as unauthorized. Checking if it's really revoked...")

                        try:
                            # Try to get a simple dialog to check if session is really revoked
                            await client.get_dialogs(limit=1)
                            logger.info(f"Client {session_name} can still access dialogs despite is_user_authorized() returning False. Keeping in active list.")
                            # Keep the client in active list since it can still function
                        except Exception as check_error:
                            check_error_msg = str(check_error).lower()
                            logger.warning(f"Client {session_name} failed dialog check: {check_error_msg}")

                            # Only consider it truly revoked if we get explicit session errors
                            if ('session' in check_error_msg and ('revoked' in check_error_msg or 'invalid' in check_error_msg)) or 'auth' in check_error_msg:
                                logger.warning(f"Client {session_name} has true SessionRevokedError. Removing permanently...")
                                logger.warning(f"This happens when: 1) Account password changed, 2) Account logged out from official app, 3) Telegram security measures")
                                # Remove from active clients first
                                async with self.tbot.active_clients_lock:
                                    if session_name in self.tbot.active_clients:
                                        del self.tbot.active_clients[session_name]
                                await client.disconnect()
                                await self.delete_session(session_name)
                                logger.info(f"Unauthorized session {session_name} has been completely removed")
                            else:
                                # Not a true session revoked error, but client is having issues
                                # Keep it in active list but log the issue
                                logger.warning(f"Client {session_name} has connectivity issues but not revoked. Keeping in active list for retry.")
                                # Don't move to inactive accounts - keep trying

                    # Sleep to avoid hitting Telegram flood limits
                    await asyncio.sleep(3)
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.warning(f"Error loading client {session_name}: {e}")

                    # Only move to inactive for very specific errors
                    # Most errors should be retried rather than making accounts inactive
                    if 'session revoked' in error_msg or 'auth' in error_msg or 'invalid' in error_msg:
                        # True authentication/session errors
                        logger.warning(f"Client {session_name} has authentication issues. Moving to inactive.")
                        async with self.tbot.active_clients_lock:
                            if session_name in self.tbot.active_clients:
                                del self.tbot.active_clients[session_name]

                        if session_name not in self.config['inactive_accounts']:
                            self.config['inactive_accounts'][session_name] = {
                                'phone': session_name,
                                'last_seen': asyncio.get_event_loop().time(),
                                'reason': 'auth_error',
                                'error_details': str(e)
                            }
                            self.config_manager.save_config(self.config)
                    else:
                        # Temporary errors - keep trying, don't make inactive
                        logger.warning(f"Temporary error with client {session_name}: {e}. Will retry on next startup.")
                        # Remove from active clients temporarily, but don't add to inactive accounts
                        async with self.tbot.active_clients_lock:
                            if session_name in self.tbot.active_clients:
                                del self.tbot.active_clients[session_name]
        except Exception as e:
            logger.error(f"Error in start_saved_clients: {e}")

    async def show_inactive_accounts(self, event):
        """
        Display list of inactive accounts for admin review.
        """
        try:
            logger.info("show_inactive_accounts called")

            # Initialize inactive accounts if not exists
            if 'inactive_accounts' not in self.config:
                self.config['inactive_accounts'] = {}

            inactive_accounts = self.config['inactive_accounts']

            if not inactive_accounts:
                await event.respond("✅ No inactive accounts found. All accounts are working properly.")
                return

            # Build response message
            message = "📋 **Inactive Accounts Report**\n\n"
            message += f"Total inactive accounts: {len(inactive_accounts)}\n\n"

            for phone, account_info in inactive_accounts.items():
                reason = account_info.get('reason', 'unknown')
                last_seen = account_info.get('last_seen', 0)
                error_details = account_info.get('error_details', 'No details available')

                # Format timestamp
                import time
                last_seen_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_seen))

                message += f"📱 **{phone}**\n"
                message += f"   Reason: {reason}\n"
                message += f"   Last seen: {last_seen_str}\n"
                message += f"   Error: {error_details[:100]}{'...' if len(error_details) > 100 else ''}\n\n"

            # Add management options
            message += "**Management Options:**\n"
            message += "• Use /start to return to main menu\n"
            message += "• Inactive accounts will be automatically reactivated when possible"

            # Send message (split if too long)
            if len(message) > 4000:
                # Split into chunks
                chunks = []
                current_chunk = ""
                lines = message.split('\n')

                for line in lines:
                    if len(current_chunk + line + '\n') > 4000:
                        chunks.append(current_chunk)
                        current_chunk = line + '\n'
                    else:
                        current_chunk += line + '\n'

                if current_chunk:
                    chunks.append(current_chunk)

                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await event.respond(chunk)
                    else:
                        await event.respond(f"(Part {i+1}/{len(chunks)})\n{chunk}")
            else:
                await event.respond(message)

        except Exception as e:
            logger.error(f"Error in show_inactive_accounts: {e}")
            await event.respond("❌ Error retrieving inactive accounts list.")

    async def reactivate_account(self, event, phone_number):
        """
        Attempt to reactivate an inactive account.
        """
        try:
            logger.info(f"reactivate_account called for {phone_number}")

            if 'inactive_accounts' not in self.config or phone_number not in self.config['inactive_accounts']:
                await event.respond(f"❌ Account {phone_number} is not in inactive accounts list.")
                return

            # Remove from inactive list and try to reload
            del self.config['inactive_accounts'][phone_number]
            self.config_manager.save_config(self.config)

            # Try to reload the account
            session_file = f"{phone_number}.session"
            if os.path.exists(session_file):
                try:
                    # Create new client instance
                    from telethon import TelegramClient
                    from src.Config import API_ID, API_HASH

                    client = TelegramClient(phone_number, API_ID, API_HASH)

                    # Try to connect and authorize
                    await client.connect()
                    if await client.is_user_authorized():
                        # Add to active clients
                        async with self.tbot.active_clients_lock:
                            self.tbot.active_clients[phone_number] = client

                        # Add back to config
                        if 'clients' not in self.config:
                            self.config['clients'] = {}
                        self.config['clients'][phone_number] = []  # Empty groups list
                        self.config_manager.save_config(self.config)

                        await event.respond(f"✅ Account {phone_number} successfully reactivated!")
                        logger.info(f"Account {phone_number} reactivated successfully")
                    else:
                        await client.disconnect()
                        await event.respond(f"❌ Account {phone_number} is still not authorized. Cannot reactivate.")
                        logger.warning(f"Account {phone_number} still not authorized during reactivation")

                except Exception as e:
                    logger.error(f"Error reactivating account {phone_number}: {e}")
                    await event.respond(f"❌ Error reactivating account {phone_number}: {str(e)}")
            else:
                await event.respond(f"❌ Session file for {phone_number} not found.")
                logger.warning(f"Session file {session_file} not found during reactivation")

        except Exception as e:
            logger.error(f"Error in reactivate_account: {e}")
            await event.respond("❌ Error during account reactivation.")

    async def disconnect_all_clients(self):
        """
        Disconnect all active Telegram clients and clear the active client list.
        """
        try:
            for session_name, client in list(self.active_clients.items()):
                try:
                    # Cleanup handlers before disconnecting to prevent memory leaks
                    if hasattr(self.tbot, 'monitor'):
                        self.tbot.monitor.cleanup_client_handlers(client)
                    await client.disconnect()
                    logger.info(f"Client {session_name} disconnected successfully.")
                except Exception as e:
                    logger.error(f"Error disconnecting client {session_name}: {e}")
            
            # Clear the active_clients dictionary
            self.active_clients.clear()
            logger.info("All clients disconnected successfully.")
        except Exception as e:
            logger.error(f"Error disconnecting clients: {e}")

    async def delete_session(self, session_name):
        """
        Delete a session file and remove it from the configuration.
        :param session_name: The name of the session to delete.
        """
        try:
            if session_name in self.active_clients:
                client = self.active_clients[session_name]
                # Cleanup handlers before disconnecting
                if hasattr(self.tbot, 'monitor'):
                    self.tbot.monitor.cleanup_client_handlers(client)
                await client.disconnect()
                del self.active_clients[session_name]
                logger.info(f"Client {session_name} disconnected and removed from active clients.")

            if session_name in self.config['clients']:
                del self.config['clients'][session_name]
                self.config_manager.save_config(self.config)

                session_file = f"{session_name}.session"
                if os.path.exists(session_file):
                    try:
                        os.remove(session_file)
                        logger.info(f"Session file {session_file} deleted successfully.")
                    except OSError as e:
                        # File is in use by another process - this is normal
                        logger.warning(f"Session file {session_file} could not be deleted (in use by another process): {e}")
                        logger.info(f"Session {session_name} removed from config but file remains (will be cleaned up later)")

                # Session deleted successfully - no need to send message as callback handler will respond
                logger.info(f"Session {session_name} deleted successfully.")
            else:
                logger.warning(f"Session {session_name} not found in configuration.")
        except Exception as e:
            logger.error(f"Error deleting session {session_name}: {e}")
            # Don't send error message here - let the callback handler handle it


class AccountHandler:
    """
    Handles all account-related operations for the Telegram bot.
    Manages account creation, authentication, and message processing.
    """

    def __init__(self, tbot):
        """
        Initialize AccountHandler with bot instance.

        Args:
            tbot: Bot instance containing configuration and client management
        """
        self.tbot = tbot
        self._conversations = {}
        self.SessionManager = tbot.client_manager

    async def add_account(self, event):
        """
        Initiates the account addition process by requesting phone number.

        Args:
            event: Telegram event containing chat information
        """
        logger.info("add_account in AccountHandler")
        chat_id = event.chat_id
        try:
            buttons = [Button.inline("Cancel", b'cancel')]
            await self.tbot.tbot.send_message(chat_id, "Please enter your phone number:", buttons=buttons)
            async with self.tbot._conversations_lock:
                self.tbot._conversations[chat_id] = 'phone_number_handler'
        except Exception as e:
            logger.error(f"Error in add_account: {e}")
            await self.tbot.tbot.send_message(chat_id, "Error occurred while adding account. Please try again.")

    async def phone_number_handler(self, event):
        """
        Handles phone number verification and initiates client connection.

        Args:
            event: Telegram event containing the phone number
        """
        logger.info("phone_number_handler in AccountHandler")
        chat_id = event.chat_id
        phone_number = event.message.text.strip()
        
        # Validate phone number
        is_valid, error_msg = InputValidator.validate_phone_number(phone_number)
        if not is_valid:
            await self.tbot.tbot.send_message(chat_id, f"❌ {error_msg}\nPlease try again.")
            return
        
        try:
            # Create client with phone number as session name
            logger.info(f"PHONE_NUMBER_HANDLER: Creating client for {phone_number}")
            client = TelegramClient(phone_number, API_ID, API_HASH)

            logger.info("PHONE_NUMBER_HANDLER: Connecting to Telegram...")
            await client.connect()

            if not await client.is_user_authorized():
                logger.info("PHONE_NUMBER_HANDLER: Not authorized, sending code request")
                # Send code request to user's phone
                await client.send_code_request(phone_number)
                await self.tbot.tbot.send_message(chat_id, "📱 Verification code sent to your Telegram account.\n\nEnter the verification code:")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations[chat_id] = 'code_handler'
                self.tbot.handlers['temp_client'] = client
                self.tbot.handlers['temp_phone'] = phone_number
                logger.info("PHONE_NUMBER_HANDLER: Code request sent successfully")
            else:
                logger.info("PHONE_NUMBER_HANDLER: Already authorized, finalizing setup")
                # Already authorized, finalize setup
                await self.finalize_client_setup(client, phone_number, chat_id)
        except Exception as e:
            logger.error(f"PHONE_NUMBER_HANDLER: Error - {e}")
            error_msg = str(e).lower()

            if 'flood' in error_msg:
                await self.tbot.tbot.send_message(chat_id, "❌ Too many requests. Please wait a few minutes and try again.")
            elif 'phone' in error_msg and 'invalid' in error_msg:
                await self.tbot.tbot.send_message(chat_id, "❌ Invalid phone number. Please check the format and try again.")
            elif 'network' in error_msg or 'connection' in error_msg:
                await self.tbot.tbot.send_message(chat_id, "❌ Network error. Please check your connection and try again.")
            elif 'api' in error_msg and 'invalid' in error_msg:
                await self.tbot.tbot.send_message(chat_id, "❌ API credentials error. Please contact the administrator.")
            else:
                await self.tbot.tbot.send_message(chat_id, f"❌ Failed to add account: {str(e)[:100]}...")

            self.cleanup_temp_handlers()

    async def code_handler(self, event):
        """
        Processes verification code and completes authentication.

        Args:
            event: Telegram event containing the verification code
        """
        try:
            logger.info("code_handler in AccountHandler")
            chat_id = event.chat_id
            code = event.message.text.strip()
            client = self.tbot.handlers.get('temp_client')
            phone_number = self.tbot.handlers.get('temp_phone')

            if not client or not phone_number:
                await self.tbot.tbot.send_message(chat_id, "Session expired or invalid. Please start over with /start.")
                self.cleanup_temp_handlers()
                return

            await client.sign_in(phone=phone_number, code=code)
            await self.finalize_client_setup(client, phone_number, chat_id)
        except SessionPasswordNeededError:
            await self.tbot.tbot.send_message(chat_id, "Two-factor authentication is enabled. Please enter your password:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[chat_id] = 'password_handler'
        except FloodWaitError as e:
            await self.tbot.tbot.send_message(chat_id, f"Too many attempts. Please wait {e.seconds} seconds and try again.")
            self.cleanup_temp_handlers()
        except Exception as e:
            logger.error(f"Error during code verification: {e}")
            await self.tbot.tbot.send_message(chat_id, f"Error verifying code: {e}. Please try again.")
            self.cleanup_temp_handlers()

    async def password_handler(self, event):
        """
        Handles 2FA password verification if required.

        Args:
            event: Telegram event containing the 2FA password
        """
        try:
            logger.info("password_handler in AccountHandler")
            chat_id = event.chat_id
            password = event.message.text.strip()
            client = self.tbot.handlers.get('temp_client')
            phone_number = self.tbot.handlers.get('temp_phone')

            if not client or not phone_number:
                await self.tbot.tbot.send_message(chat_id, "Session expired or invalid. Please start over with /start.")
                self.cleanup_temp_handlers()
                return

            await client.sign_in(password=password)
            await self.finalize_client_setup(client, phone_number, chat_id)
        except FloodWaitError as e:
            await self.tbot.tbot.send_message(chat_id, f"Too many attempts. Please wait {e.seconds} seconds and try again.")
            self.cleanup_temp_handlers()
        except Exception as e:
            logger.error(f"Error during password verification: {e}")
            await self.tbot.tbot.send_message(chat_id, f"Error verifying password: {e}. Please try again.")
            self.cleanup_temp_handlers()

    async def finalize_client_setup(self, client, phone_number, chat_id):
        """
        Completes client setup and saves configuration.

        Args:
            client: Authorized TelegramClient instance
            phone_number: User's phone number
            chat_id: Chat ID for response messages
        """
        logger.info("finalize_client_setup in AccountHandler")
        try:
            session_name = f"{phone_number}"
            client.session.save()

            if not isinstance(self.tbot.config['clients'], dict):
                logger.warning("'clients' is not a dictionary. Initializing it as an empty dictionary.")
                self.tbot.config['clients'] = {}

            self.tbot.config['clients'][session_name] = []
            self.tbot.config_manager.save_config(self.tbot.config)

            # Use lock when modifying active_clients
            async with self.tbot.active_clients_lock:
                self.tbot.active_clients[session_name] = client
            
            # Set up message monitoring for this new client
            if not hasattr(client, '_message_processing_set'):
                await self.tbot.monitor.process_messages_for_client(client)
                client._message_processing_set = True

            await self.tbot.tbot.send_message(chat_id, f"Account {phone_number} added successfully!")
            self.cleanup_temp_handlers()

        except Exception as e:
            logger.error(f"Error in finalize_client_setup: {e}")
            await self.tbot.tbot.send_message(chat_id, "Error occurred while finalizing setup.")
            self.cleanup_temp_handlers()

    def cleanup_temp_handlers(self):
        """
        Removes temporary handlers and data after setup completion.
        """
        logger.info("cleanup_temp_handlers in AccountHandler")
        try:
            self.tbot.handlers.pop('temp_client', None)
            self.tbot.handlers.pop('temp_phone', None)
        except Exception as e:
            logger.error(f"Error in cleanup_temp_handlers: {e}")

    async def update_groups(self, event):
        """
        Updates group information for all clients.

        Args:
            event: Telegram event triggering the update
        """
        logger.info("Started update_groups process.")
        groups_per_client = {}
        await self.SessionManager.detect_sessions()

        try:
            status_message = await event.respond("Please wait, identifying groups for each client...")

            json_data = {
                "TARGET_GROUPS": [],
                "KEYWORDS": [],
                "IGNORE_USERS": [],
                "clients": []
            }

            if os.path.exists(CLIENTS_JSON_PATH):
                try:
                    with open(CLIENTS_JSON_PATH, "r", encoding='utf-8') as json_file:
                        loaded_data = json.loads(json_file.read())
                        json_data.update(loaded_data)
                        if isinstance(json_data["clients"], list):
                            json_data["clients"] = {session: [] for session in json_data["clients"]}
                    logger.info("Loaded existing client data from clients.json.")
                except json.JSONDecodeError as e:
                    logger.error("Error decoding clients.json.", exc_info=True)

            # Get a snapshot of active clients to avoid holding the lock during long operations
            async with self.tbot.active_clients_lock:
                active_clients_snapshot = list(self.tbot.active_clients.items())
            
            for session_name, client in active_clients_snapshot:
                try:
                    logger.info(f"Processing client: {session_name}")
                    group_ids = set()

                    # Process dialogs in batches for better performance
                    batch_count = 0
                    dialog_limit = 5000  # Reasonable limit to prevent excessive processing
                    
                    async for dialog in client.iter_dialogs(limit=dialog_limit):
                        try:
                            if isinstance(dialog.entity, (Chat, Channel)) and not (
                                isinstance(dialog.entity, Channel) and dialog.entity.broadcast
                            ):
                                group_ids.add(dialog.entity.id)
                            
                            batch_count += 1
                            
                            # Rate limiting and progress updates
                            if batch_count % GROUPS_BATCH_SIZE == 0:
                                await asyncio.sleep(1)  # Shorter sleep for better responsiveness
                                
                            if len(group_ids) % 20 == 0:
                                await status_message.edit(f"Found {len(group_ids)} groups for {session_name}...")
                                
                        except Exception as e:
                            logger.error(f"Error processing dialog for client {session_name}.", exc_info=True)
                            continue

                    groups_per_client[session_name] = list(group_ids)
                    logger.info(f"Found {len(group_ids)} groups for client {session_name}.")
                    await status_message.edit(f"Found {len(group_ids)} groups for {session_name}.")
                    await asyncio.sleep(GROUPS_UPDATE_SLEEP)

                except FloodWaitError as e:
                    wait_time = e.seconds
                    logger.warning(f"FloodWaitError: Sleeping for {wait_time} seconds for client {session_name}.")
                    await status_message.edit(f"Rate limited. Waiting for {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error while processing client {session_name}.", exc_info=True)
                    continue

            for session_name, group_ids in groups_per_client.items():
                if session_name in json_data["clients"]:
                    existing_groups = json_data["clients"][session_name]
                    if not isinstance(existing_groups, list):
                        existing_groups = []
                    json_data["clients"][session_name] = list(set(existing_groups + group_ids))
                else:
                    json_data["clients"][session_name] = group_ids

            with open(CLIENTS_JSON_PATH, "w", encoding='utf-8') as json_file:
                json.dump(json_data, json_file, indent=4, ensure_ascii=False)
                logger.info(f"Saved updated client data for {len(groups_per_client)} clients to clients.json.")

            await status_message.edit(f"That's it, groups identified and saved successfully for all clients!")

        except Exception as e:
            logger.error("Critical error in update_groups function.", exc_info=True)
            await event.respond(f"Error identifying groups: {str(e)}")


    async def show_accounts(self, event):
        """
        Display all registered accounts with their current status and controls.

        Args:
            event: Telegram event triggering the account display
        """
        logger.info("Executing show_accounts method in AccountHandler")

        try:
            clients_data = self.tbot.config.get('clients', {})
            inactive_data = self.tbot.config.get('inactive_accounts', {})

            # Get active clients snapshot
            async with self.tbot.active_clients_lock:
                active_sessions = set(self.tbot.active_clients.keys())

            messages = []

            # Process active/inactive clients from clients_data
            if isinstance(clients_data, dict) and clients_data:
                for session, groups in clients_data.items():
                    try:
                        phone = session.replace('.session', '') if session else 'Unknown'
                        groups_count = len(groups) if isinstance(groups, list) else 0
                        is_active = session in active_sessions
                        status = "🟢 Active" if is_active else "🔴 Inactive"

                        logger.debug(f"Processing account: {session}, Status: {status}, Groups: {groups_count}")

                        text = (
                            f"📱 Phone: {phone}\n"
                            f"👥 Groups: {groups_count}\n"
                            f"📊 Status: {status}\n"
                        )

                        buttons = Keyboard.toggle_and_delete_keyboard(status, session)
                        messages.append((text, buttons))
                    except Exception as e:
                        logger.error(f"Error processing account {session}: {e}", exc_info=True)

            # Process truly inactive accounts (those in inactive_accounts but not in clients)
            if isinstance(inactive_data, dict) and inactive_data:
                for session, account_info in inactive_data.items():
                    try:
                        # Skip if already processed above
                        if session in clients_data:
                            continue

                        phone = account_info.get('phone', session)
                        reason = account_info.get('reason', 'unknown')
                        last_seen = account_info.get('last_seen', 0)

                        # Format timestamp
                        import time
                        try:
                            last_seen_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_seen))
                        except:
                            last_seen_str = 'Unknown'

                        status = "❌ Inactive (Auth Error)"

                        logger.debug(f"Processing inactive account: {session}, Reason: {reason}")

                        text = (
                            f"📱 Phone: {phone}\n"
                            f"👥 Groups: N/A\n"
                            f"📊 Status: {status}\n"
                            f"⚠️ Reason: {reason}\n"
                            f"🕒 Last seen: {last_seen_str}\n"
                        )

                        buttons = Keyboard.toggle_and_delete_keyboard(status, session)
                        messages.append((text, buttons))
                    except Exception as e:
                        logger.error(f"Error processing inactive account {session}: {e}", exc_info=True)

            if not messages:
                await event.respond("No accounts found.")
                logger.warning("No accounts found in the configuration.")
                return

            for message_text, message_buttons in messages:
                try:
                    await event.respond(message_text, buttons=message_buttons)
                    logger.info(f"Sent account details for session: {message_text.split(' ')[1]}.")
                except Exception as e:
                    logger.error(f"Error sending message for account: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Critical error in show_accounts: {e}", exc_info=True)
            await event.respond("Error showing accounts. Please try again.")

    async def toggle_client(self, session: str, event):
        """
        Toggle the active/inactive status of a client account.

        Args:
            session (str): Session identifier for the account
            event: Telegram event triggering the toggle
        """
        logger.info(f"toggle_client called for session: {session}")
        try:
            if session not in self.tbot.config['clients']:
                logger.warning(f"Session {session} not found in clients.")
                await event.respond("Account not found.")
                return

            # Check current status with lock
            async with self.tbot.active_clients_lock:
                currently_active = session in self.tbot.active_clients
            
            logger.info(f"Current status for {session}: {'Active' if currently_active else 'Inactive'}")

            if currently_active:
                logger.info(f"Disabling client: {session}")
                # Use lock when modifying active_clients
                async with self.tbot.active_clients_lock:
                    client = self.tbot.active_clients[session]
                    # Cleanup handlers before disconnecting
                    if hasattr(self.tbot, 'monitor'):
                        self.tbot.monitor.cleanup_client_handlers(client)
                    await client.disconnect()
                    del self.tbot.active_clients[session]
                logger.info(f"Client {session} disabled successfully.")
                await event.respond(f"Account {session} disabled.")
            else:
                logger.info(f"Enabling client: {session}")
                try:
                    # Check if session file exists
                    session_file = f"{session}.session"
                    if not os.path.exists(session_file):
                        await event.respond(f"❌ فایل session برای حساب {session} یافت نشد.")
                        logger.error(f"Session file {session_file} not found")
                        return

                    # Try to create client and connect - avoid database operations initially
                    client = TelegramClient(session, API_ID, API_HASH)

                    # Try to connect and check authorization without full start
                    try:
                        # Connect first
                        await client.connect()

                        # Check authorization
                        if await client.is_user_authorized():
                            # Client is authorized, add to active clients
                            async with self.tbot.active_clients_lock:
                                self.tbot.active_clients[session] = client

                            # Set up message monitoring for this newly enabled client
                            if hasattr(self.tbot, 'monitor') and not hasattr(client, '_message_processing_set'):
                                await self.tbot.monitor.process_messages_for_client(client)
                                client._message_processing_set = True

                            logger.info(f"Client {session} enabled successfully.")
                            await event.respond(f"✅ حساب {session} فعال شد.")

                            # Remove from inactive accounts if it was there
                            if 'inactive_accounts' in self.tbot.config and session in self.tbot.config['inactive_accounts']:
                                del self.tbot.config['inactive_accounts'][session]
                                self.tbot.config_manager.save_config(self.tbot.config)
                        else:
                            # Client is not authorized, move to inactive accounts
                            await client.disconnect()
                            if 'inactive_accounts' not in self.tbot.config:
                                self.tbot.config['inactive_accounts'] = {}
                            self.tbot.config['inactive_accounts'][session] = {
                                'phone': session,
                                'last_seen': self.tbot.loop.time(),
                                'reason': 'not_authorized_on_reactivation',
                                'error_details': 'Client not authorized'
                            }
                            self.tbot.config_manager.save_config(self.tbot.config)
                            await event.respond(f"❌ حساب {session} توسط تلگرام غیرمجاز شده است.")
                            logger.warning(f"Client {session} not authorized on reactivation")

                    except Exception as e:
                        await client.disconnect()
                        error_msg = str(e).lower()
                        logger.error(f"Error enabling client {session}: {e}")

                        # Handle different types of errors
                        if 'database is locked' in error_msg or 'sqlite' in error_msg:
                            # Database lock - this is temporary, keep the account in config for retry
                            await event.respond(f"⚠️ حساب {session} موقتاً غیرفعال است (مشکل دیتابیس). بعداً دوباره امتحان کنید.")
                            logger.warning(f"Database lock for {session}, will retry later")
                        elif 'flood' in error_msg or 'too many' in error_msg:
                            # Flood control - temporary issue
                            await event.respond(f"⚠️ حساب {session} موقتاً غیرفعال است (محدودیت تلگرام). بعداً دوباره امتحان کنید.")
                            logger.warning(f"Flood control for {session}, will retry later")
                        elif 'network' in error_msg or 'connection' in error_msg:
                            # Network issue - temporary
                            await event.respond(f"⚠️ حساب {session} موقتاً غیرفعال است (مشکل شبکه). بعداً دوباره امتحان کنید.")
                            logger.warning(f"Network issue for {session}, will retry later")
                        else:
                            # Other error - move to inactive accounts for admin review
                            if 'inactive_accounts' not in self.tbot.config:
                                self.tbot.config['inactive_accounts'] = {}
                            self.tbot.config['inactive_accounts'][session] = {
                                'phone': session,
                                'last_seen': self.tbot.loop.time(),
                                'reason': 'connection_error',
                                'error_details': str(e)
                            }
                            self.tbot.config_manager.save_config(self.tbot.config)
                            await event.respond(f"❌ خطا در فعال‌سازی حساب {session}: {str(e)[:100]}...")

                except Exception as e:
                    logger.error(f"Error in toggle_client enable section: {e}")
                    await event.respond(f"❌ خطا در فعال‌سازی حساب {session}.")

            logger.info("Saving updated configuration.")
            self.tbot.config_manager.save_config(self.tbot.config)

        except Exception as e:
            logger.error(f"Error toggling client {session}: {e}", exc_info=True)
            try:
                await event.respond("❌ خطا در تغییر وضعیت حساب.")
            except Exception as resp_e:
                logger.error(f"Failed to send error response: {resp_e}")

    async def delete_client(self, session: str, event):
        """
        Permanently delete a client account and its associated data.

        Args:
            session (str): Session identifier for the account to delete
            event: Telegram event triggering the deletion
        """
        logger.info(f"delete_client called for session: {session}")
        try:
            # Check if client is active with lock
            async with self.tbot.active_clients_lock:
                is_active = session in self.tbot.active_clients
            
            if is_active:
                logger.info(f"Disconnecting active client: {session}")
                # Use lock when modifying active_clients
                async with self.tbot.active_clients_lock:
                    client = self.tbot.active_clients[session]
                    # Cleanup handlers before disconnecting
                    if hasattr(self.tbot, 'monitor'):
                        self.tbot.monitor.cleanup_client_handlers(client)
                    await client.disconnect()
                    del self.tbot.active_clients[session]
                logger.info(f"Client {session} disconnected and removed from active clients.")

            if session in self.tbot.config['clients']:
                logger.info(f"Removing session {session} from configuration.")
                del self.tbot.config['clients'][session]
                self.tbot.config_manager.save_config(self.tbot.config)

                session_file = f"{session}.session"
                if os.path.exists(session_file):
                    try:
                        logger.info(f"Deleting session file: {session_file}")
                        os.remove(session_file)
                    except OSError as e:
                        # File is in use by another process - this is normal
                        logger.warning(f"Session file {session_file} could not be deleted (in use by another process): {e}")
                        logger.info(f"Session {session} removed from config but file remains (will be cleaned up later)")

                await event.respond("Account deleted successfully.")
            else:
                logger.warning(f"Session {session} not found in configuration.")
                await event.respond("Account not found.")

        except Exception as e:
            logger.error(f"Error deleting client {session}: {e}", exc_info=True)
            await event.respond("Error deleting account.")

