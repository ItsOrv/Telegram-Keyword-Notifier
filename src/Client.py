import os
import logging
import asyncio
from telethon import TelegramClient, events, Button
from src.Config import ConfigManager, API_ID, API_HASH, PORTS, ADMIN_ID
from src.Config import API_ID, API_HASH, CHANNEL_ID, ADMIN_ID ,CLIENTS_JSON_PATH, RATE_LIMIT_SLEEP, GROUPS_BATCH_SIZE, GROUPS_UPDATE_SLEEP

import os
import logging
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from src.Keyboards import Keyboard


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

    def detect_sessions(self):
        """
        Detect and load Telegram client sessions from the configuration.
        Adds sessions to `active_clients` if they are not already active.
        """
        try:
            if not isinstance(self.config.get('clients', {}), dict):
                logger.warning("'clients' is not a dictionary. Initializing it as an empty dictionary.")
                self.config['clients'] = {}

            for session_name in list(self.config['clients']):
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

            for session_name, client in list(self.active_clients.items()):
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
                        await self.notify_admin_unauthorized(session_name)

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
            for session_name, client in list(self.active_clients.items()):
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

    async def notify_admin_unauthorized(self, session_name):
        """
        Notify the admin that a session is not authorized and provide options to delete or ignore the session.
        :param session_name: The name of the unauthorized session.
        """
        try:
            buttons = [
                [Button.inline("Delete", f"delete_{session_name}"), Button.inline("Ignore", f"ignore_{session_name}")]
            ]
            await self.tbot.send_message(
                int(ADMIN_ID),
                f"Session {session_name} is not authorized. What would you like to do?",
                buttons=buttons
            )
            logger.info(f"Notification sent to admin for unauthorized session: {session_name}")
        except Exception as e:
            logger.error(f"Error notifying admin about unauthorized session {session_name}: {e}")

    async def delete_session(self, session_name):
        """
        Delete a session file and remove it from the configuration.
        :param session_name: The name of the session to delete.
        """
        try:
            if session_name in self.active_clients:
                client = self.active_clients[session_name]
                await client.disconnect()
                del self.active_clients[session_name]
                logger.info(f"Client {session_name} disconnected and removed from active clients.")

            if session_name in self.config['clients']:
                del self.config['clients'][session_name]
                self.config_manager.save_config(self.config)

                session_file = os.path.join("..", f"{session_name}.session")
                if os.path.exists(session_file):
                    os.remove(session_file)
                    logger.info(f"Session file {session_file} deleted successfully.")
                else:
                    logger.warning(f"Session file {session_file} not found.")

                await self.tbot.send_message(int(ADMIN_ID), f"Session {session_name} deleted successfully.")
            else:
                logger.warning(f"Session {session_name} not found in configuration.")
                await self.tbot.send_message(int(ADMIN_ID), f"Session {session_name} not found.")
        except Exception as e:
            logger.error(f"Error deleting session {session_name}: {e}")
            await self.tbot.send_message(int(ADMIN_ID), f"Error deleting session {session_name}.")


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
        try:
            client = TelegramClient(phone_number, API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                await self.tbot.tbot.send_message(chat_id, "Authorizing...")
                await client.send_code_request(phone_number)
                await self.tbot.tbot.send_message(chat_id, "Enter the verification code:")
                self.tbot._conversations[chat_id] = 'code_handler'
                self.tbot.handlers['temp_client'] = client
                self.tbot.handlers['temp_phone'] = phone_number
            else:
                await self.finalize_client_setup(client, phone_number, chat_id)

        except Exception as e:
            logger.error(f"Error in phone_number_handler: {e}")
            await self.tbot.tbot.send_message(chat_id, "Error occurred. Please try again.")
            self.cleanup_temp_handlers()

    async def code_handler(self, event):
        """
        Processes verification code and completes authentication.

        Args:
            event: Telegram event containing the verification code
        """
        logger.info("code_handler in AccountHandler")
        chat_id = event.chat_id
        code = event.message.text.strip()
        client = self.tbot.handlers.get('temp_client')
        phone_number = self.tbot.handlers.get('temp_phone')
        try:
            await client.sign_in(phone_number, code)
            await self.finalize_client_setup(client, phone_number, chat_id)
        except SessionPasswordNeededError:
            await self.tbot.tbot.send_message(chat_id, "Enter your 2FA password:")
            self.tbot._conversations[chat_id] = 'password_handler'
        except Exception as e:
            logger.error(f"Error in code_handler: {e}")
            await self.tbot.tbot.send_message(chat_id, "Error occurred. Please try again.")
            self.cleanup_temp_handlers()

    async def password_handler(self, event):
        """
        Handles 2FA password verification if required.

        Args:
            event: Telegram event containing the 2FA password
        """
        logger.info("password_handler in AccountHandler")
        chat_id = event.chat_id
        password = event.message.text.strip()
        client = self.tbot.handlers.get('temp_client')
        phone_number = self.tbot.handlers.get('temp_phone')
        try:
            await client.sign_in(password=password)
            await self.finalize_client_setup(client, phone_number, chat_id)
        except Exception as e:
            logger.error(f"Error in password_handler: {e}")
            await self.tbot.tbot.send_message(chat_id, "Error occurred. Please try again.")
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

            self.tbot.active_clients[session_name] = client
            client.add_event_handler(self.process_message, events.NewMessage())

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
        self.SessionManager.detect_sessions()

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

            for session_name, client in self.tbot.active_clients.items():
                try:
                    logger.info(f"Processing client: {session_name}")
                    group_ids = set()

                    async for dialog in client.iter_dialogs(limit=None):
                        try:
                            if isinstance(dialog.entity, (Chat, Channel)) and not (
                                isinstance(dialog.entity, Channel) and dialog.entity.broadcast
                            ):
                                group_ids.add(dialog.entity.id)

                            if len(group_ids) % GROUPS_BATCH_SIZE == 0:
                                await asyncio.sleep(RATE_LIMIT_SLEEP)

                        except Exception as e:
                            logger.error(f"Error processing dialog for client {session_name}.", exc_info=True)
                            continue

                        if len(group_ids) % 20 == 0:
                            await status_message.edit(f"Found {len(group_ids)} groups for {session_name}...")

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

    async def process_messages_for_client(self, client):
        """
        Sets up message processing for a specific client.

        Args:
            client: TelegramClient instance to process messages for
        """
        logger.info("Setting up message processing for client.")

        @client.on(events.NewMessage)
        async def process_message(event):
            """
            Processes and forwards new messages based on configured filters.

            Args:
                event: NewMessage event from Telegram
            """
            try:
                logger.debug("Received new message event.")

                message = event.message.text
                if not message:
                    logger.debug("Message text is empty. Skipping.")
                    return

                sender = await event.get_sender()
                if not sender:
                    logger.warning("Could not fetch sender information. Skipping message.")
                    sender_info = "Unknown Sender"
                else:
                    sender_info = f"User: {getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}\n" \
                                  f"• User ID: `{sender.id}`\n"

                if sender and sender.id in self.tbot.config['IGNORE_USERS']:
                    logger.info(f"Message from ignored user {sender.id}. Skipping.")
                    return

                if not any(keyword.lower() in message.lower() for keyword in self.tbot.config['KEYWORDS']):
                    logger.debug("Message does not contain any configured keywords. Skipping.")
                    return

                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', 'Unknown Chat')
                logger.info(f"Processing message from chat: {chat_title}")

                account_name = client.session.filename.replace('.session', '')

                text = (
                    f"Account: {account_name}\n"
                    f"{sender_info}"
                    f"• Chat: {chat_title}\n\n"
                    f"• Message:\n{message}\n"
                )

                if hasattr(chat, 'username') and chat.username:
                    message_link = f"https://t.me/{chat.username}/{event.id}"
                else:
                    chat_id = str(event.chat_id).replace('-100', '', 1)
                    message_link = f"https://t.me/c/{chat_id}/{event.id}"

                buttons = Keyboard.channel_message_keyboard(message_link, sender.id if sender else 0)

                await self.tbot.tbot.send_message(
                    CHANNEL_ID,
                    text,
                    buttons=buttons,
                    link_preview=False
                )

                logger.info(f"Forwarded message from user {sender.id if sender else 'Unknown'} in chat {chat_title}.")

            except Exception as e:
                logger.error("Error processing message.", exc_info=True)

    async def show_accounts(self, event):
        """
        Display all registered accounts with their current status and controls.

        Args:
            event: Telegram event triggering the account display
        """
        logger.info("Executing show_accounts method in AccountHandler")

        try:
            clients_data = self.tbot.config.get('clients', {})
            logger.debug(f"Retrieved clients data: {clients_data}")

            if not isinstance(clients_data, dict) or not clients_data:
                await event.respond("No accounts added yet.")
                logger.warning("No accounts found in the configuration.")
                return

            messages = []

            for session, groups in clients_data.items():
                try:
                    phone = session.replace('.session', '') if session else 'Unknown'
                    groups_count = len(groups)
                    status = "🟢 Active" if session in self.tbot.active_clients else "🔴 Inactive"

                    logger.debug(f"Processing account: {session}, Status: {status}, Groups: {groups_count}")

                    text = (
                        f"• Phone: {phone}\n"
                        f"• Groups: {groups_count}\n"
                        f"• Status: {status}\n"
                    )

                    buttons = Keyboard.toggle_and_delete_keyboard(status, session)
                    messages.append((text, buttons))
                except Exception as e:
                    logger.error(f"Error processing account {session}: {e}", exc_info=True)

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

            currently_active = session in self.tbot.active_clients
            logger.info(f"Current status for {session}: {'Active' if currently_active else 'Inactive'}")

            if currently_active:
                logger.info(f"Disabling client: {session}")
                client = self.tbot.active_clients[session]
                await client.disconnect()
                del self.tbot.active_clients[session]
                logger.info(f"Client {session} disabled successfully.")
                await event.respond(f"Account {session} disabled.")
            else:
                logger.info(f"Enabling client: {session}")
                client = TelegramClient(session, API_ID, API_HASH)
                await client.start()
                self.tbot.active_clients[session] = client
                logger.info(f"Client {session} enabled successfully.")
                await event.respond(f"Account {session} enabled.")

            logger.info("Saving updated configuration.")
            self.tbot.config_manager.save_config(self.tbot.config)

        except Exception as e:
            logger.error(f"Error toggling client {session}: {e}", exc_info=True)
            await event.respond("Error toggling account status.")

    async def delete_client(self, session: str, event):
        """
        Permanently delete a client account and its associated data.

        Args:
            session (str): Session identifier for the account to delete
            event: Telegram event triggering the deletion
        """
        logger.info(f"delete_client called for session: {session}")
        try:
            if session in self.tbot.active_clients:
                logger.info(f"Disconnecting active client: {session}")
                client = self.tbot.active_clients[session]
                await client.disconnect()
                del self.tbot.active_clients[session]
                logger.info(f"Client {session} disconnected and removed from active clients.")

            if session in self.tbot.config['clients']:
                logger.info(f"Removing session {session} from configuration.")
                del self.tbot.config['clients'][session]
                self.tbot.config_manager.save_config(self.tbot.config)

                session_file = f"{session}"
                if os.path.exists(session_file):
                    logger.info(f"Deleting session file: {session_file}")
                    os.remove(session_file)
                else:
                    logger.warning(f"Session file {session_file} not found.")

                await event.respond("Account deleted successfully.")
            else:
                logger.warning(f"Session {session} not found in configuration.")
                await event.respond("Account not found.")

        except Exception as e:
            logger.error(f"Error deleting client {session}: {e}", exc_info=True)
            await event.respond("Error deleting account.")

    async def process_message(self, client):
        """Process messages for a specific client"""
        try:
            # Add your message processing logic here
            pass
        except Exception as e:
            logger.error(f"Error processing message for client {client}: {e}")
