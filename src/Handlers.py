import os
import logging
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from src.Config import API_ID, API_HASH, CHANNEL_ID, ADMIN_ID
from src.Client import ClientManager
from src.actions import Actions

# Setting up the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CLIENTS_JSON_PATH = "clients.json" 
RATE_LIMIT_SLEEP = 2
GROUPS_BATCH_SIZE = 50
GROUPS_UPDATE_SLEEP = 3

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
        self.ClientManager = tbot.client_manager 

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
        self.ClientManager.detect_sessions()

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
                self.tbot.config_manager.save_config()

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

class CallbackHandler:
    def __init__(self, tbot):
        self.tbot = tbot
        self.account_handler = AccountHandler(self.tbot)
        self.keyword_handler = KeywordHandler(self.tbot)
        self.stats_handler = StatsHandler(self.tbot)

        self.callback_actions = {
            'add_account': self.account_handler.add_account,
            'list_accounts': self.account_handler.show_accounts,
            'update_groups': self.account_handler.update_groups,
            'add_keyword': self.keyword_handler.add_keyword_handler,
            'remove_keyword': self.keyword_handler.remove_keyword_handler,
            'ignore_user': self.keyword_handler.ignore_user_handler,
            'remove_ignore_user': self.keyword_handler.delete_ignore_user_handler,
            'show_stats': self.stats_handler.show_stats,
            'monitor_mode': self.show_monitor_keyboard,
            'account_management': self.show_account_management_keyboard,
            'bulk_operations': self.show_bulk_operations_keyboard,
            'individual_keyboard': self.show_individual_keyboard,
            'report': self.show_report_keyboard,
            'exit': self.show_start_keyboard,
        }

    def show_start_keyboard(self, event):
        return Keyboard.show_keyboard('start', event)

    def show_monitor_keyboard(self, event):
        """Handles the monitor mode keyboard display"""
        return Keyboard.show_keyboard('monitor', event)

    def show_account_management_keyboard(self, event):
        """Handles the account management keyboard display"""
        return Keyboard.show_keyboard('account_management', event)

    def show_bulk_operations_keyboard(self, event):
        """Handles the bulk operations keyboard display"""
        return Keyboard.show_keyboard('bulk', event)

    def show_individual_keyboard(self, event):
        """Handles the individual operations keyboard display"""
        return Keyboard.show_keyboard('individual_keyboard', event)

    def show_report_keyboard(self, event):
        """Handles the report keyboard display"""
        return Keyboard.show_keyboard('report', event)

    
    async def callback_handler(self, event):
        """Handle callback queries"""
        logger.info("callback_handler in CallbackHandler")
        try:
            if event.sender_id != int(ADMIN_ID):
                await event.respond("You are not the admin")
                return

            data = event.data.decode()

            if data == 'cancel':
                chat_id = event.chat_id
                self.tbot._conversations.pop(chat_id, None)
                await event.delete()
                return

            # Handle special cases (e.g., phone number request, toggle, delete, ignore)
            if data == 'request_phone_number':
                logger.info("request_phone_number in callback_handler")
                await event.respond("Please enter your phone number:")
                self.tbot._conversations[event.chat_id] = 'phone_number_handler'
            elif data.startswith('ignore_'):
                parts = data.split('_')
                if len(parts) == 2 and parts[1].isdigit():
                    user_id = int(parts[1])
                    await self.keyword_handler.ignore_user(user_id, event)
                else:
                    logger.error(f"Invalid user ID in callback data: {data}")
                    await event.respond("Invalid user ID.")
            elif data.startswith('toggle_'):
                session = data.replace('toggle_', '')
                await self.account_handler.toggle_client(session, event)
            elif data.startswith('delete_'):
                session = data.replace('delete_', '')
                await self.account_handler.delete_client(session, event)
            else:
                # Handle standard actions based on callback data
                action = self.callback_actions.get(data)
                if action:
                    logger.info(f"{data} in callback_handler")
                    await action(event)
                else:
                    logger.error(f"No handler found for callback data: {data}")
                    await event.respond("Unknown command.")

        except Exception as e:
            logger.error(f"Error in callback_handler: {e}")
            await event.respond("Error processing request. Please try again.")




class CommandHandler:
    def __init__(self, tbot):
        self.bot = tbot

    async def start_command(self, event):
        """Handle /start command"""
        logger.info("start command in CommandHandler")
        try:
            if event.sender_id != int(ADMIN_ID):
                await event.respond("You are not the admin")
                return

            buttons = Keyboard.start_keyboard()
            await event.respond(
                "Telegram Management Bot\n\n",
                buttons=buttons
            )

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await event.respond("Error showing menu. Please try again.")


class KeywordHandler:
    def __init__(self, tbot):
        self.tbot = tbot

    async def add_keyword_handler(self, event):
        """Add a keyword to monitor"""
        logger.info("add_keyword_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                buttons = [Button.inline("Cancel", b'cancel')]
                await event.respond("Please enter the keyword you want to add.", buttons=buttons)
                self.tbot._conversations[event.chat_id] = 'add_keyword_handler'
                return

            keyword = str(event.message.text.strip())
            if keyword not in self.tbot.config['KEYWORDS']:
                self.tbot.config['KEYWORDS'].append(keyword)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"Keyword '{keyword}' added successfully")
            else:
                await event.respond(f"Keyword '{keyword}' already exists")

            keywords = ', '.join(str(k) for k in self.tbot.config['KEYWORDS'])
            await event.respond(f"📝 Current keywords: {keywords}")

        except Exception as e:
            logger.error(f"Error adding keyword: {e}")
            await event.respond("Error adding keyword")

    async def remove_keyword_handler(self, event):
        """Remove a keyword from monitoring"""
        logger.info("remove_keyword_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                buttons = [Button.inline("Cancel", b'cancel')]
                await event.respond("Please enter the keyword you want to remove.", buttons=buttons)
                self.tbot._conversations[event.chat_id] = 'remove_keyword_handler'
                return

            keyword = str(event.message.text.strip())
            if keyword in self.tbot.config['KEYWORDS']:
                self.tbot.config['KEYWORDS'].remove(keyword)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"Keyword '{keyword}' removed successfully")
            else:
                await event.respond(f"Keyword '{keyword}' not found")

            keywords = ', '.join(str(k) for k in self.tbot.config['KEYWORDS'])
            await event.respond(f"Current keywords: {keywords}")

        except Exception as e:
            logger.error(f"Error removing keyword: {e}")
            await event.respond("Error removing keyword")

    async def ignore_user_handler(self, event):
        """Ignore a user from further interaction"""
        logger.info("ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                buttons = [Button.inline("Cancel", b'cancel')]
                await event.respond("Please enter the user ID you want to ignore.", buttons=buttons)
                self.tbot._conversations[event.chat_id] = 'ignore_user_handler'
                return

            user_id = int(event.message.text.strip())
            if user_id not in self.tbot.config['IGNORE_USERS']:
                self.tbot.config['IGNORE_USERS'].append(user_id)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"User ID {user_id} is now ignored")
            else:
                await event.respond(f"User ID {user_id} is already ignored")

            ignored_users = ', '.join(str(u) for u in self.tbot.config['IGNORE_USERS'])
            await event.respond(f"Ignored users: {ignored_users}")

        except Exception as e:
            logger.error(f"Error ignoring user: {e}")
            await event.respond("Error ignoring user")

    async def delete_ignore_user_handler(self, event):
        """Remove a user from the ignore list"""
        logger.info("delete_ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                buttons = [Button.inline("Cancel", b'cancel')]
                await event.respond("Please enter the user ID you want to stop ignoring.", buttons=buttons)
                self.tbot._conversations[event.chat_id] = 'delete_ignore_user_handler'
                return

            user_id = int(event.message.text.strip())
            if user_id in self.tbot.config['IGNORE_USERS']:
                self.tbot.config['IGNORE_USERS'].remove(user_id)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"User ID {user_id} is no longer ignored")
            else:
                await event.respond(f"User ID {user_id} not found in ignored list")

            ignored_users = ', '.join(str(u) for u in self.tbot.config['IGNORE_USERS'])
            await event.respond(f"Ignored users: {ignored_users}")

        except Exception as e:
            logger.error(f"Error deleting ignored user: {e}")
            await event.respond("Error deleting ignored user")

    async def ignore_user(self, user_id, event): # for channel button
        """Ignore a user from further interaction."""
        logger.info("ignore_user in KeywordHandler")
        try:
            if user_id not in self.tbot.config['IGNORE_USERS']:
                self.tbot.config['IGNORE_USERS'].append(user_id)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"User ID {user_id} is now ignored")
            else:
                await event.respond(f"User ID {user_id} is already ignored")

        except Exception as e:
            logger.error(f"Error ignoring user: {e}")
            await event.respond("Error ignoring user")


class MessageHandler:
    def __init__(self, tbot):
        self.tbot = tbot
        self.account_handler = AccountHandler(tbot)
        self.keyword_handler = KeywordHandler(tbot)


    async def message_handler(self, event):
        """Handle incoming messages based on conversation state"""
        logger.info("message_handler in MessageHandler")

        if event.sender_id != int(ADMIN_ID):
            await event.respond("You are not the admin")
            return
        
        if event.chat_id in self.tbot._conversations:
            handler_name = self.tbot._conversations[event.chat_id]
            if handler_name == 'phone_number_handler':
                await self.account_handler.phone_number_handler(event)
                return True
            elif handler_name == 'code_handler':
                await self.account_handler.code_handler(event)
                return True
            elif handler_name == 'password_handler':
                await self.account_handler.password_handler(event)
                return True
            elif handler_name == 'ignore_user_handler':
                await self.keyword_handler.ignore_user_handler(event)
                return True
            elif handler_name == 'delete_ignore_user_handler':
                await self.keyword_handler.delete_ignore_user_handler(event)
                return True
            elif handler_name == 'add_keyword_handler':
                await self.keyword_handler.add_keyword_handler(event)
                return True
            elif handler_name == 'remove_keyword_handler':
                await self.keyword_handler.remove_keyword_handler(event)
                return True

        return False


class StatsHandler:
    def __init__(self, tbot):
        self.tbot = tbot

    #PASS
    async def show_stats(self, event):
        """Show bot statistics"""
        logger.info("show_stats in StatsHandler")
        try:
            stats = {
                "Total Accounts": len(self.tbot.config['clients']),
                "Active Accounts": len(self.tbot.active_clients),
                "Keywords": len(self.tbot.config['KEYWORDS']),
                "Ignored Users": len(self.tbot.config['IGNORE_USERS'])
            }

            text = "Bot Statistics\n\n"
            for key, value in stats.items():
                text += f"• {key}: {value}\n"

            await event.respond(text)

        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await event.respond("Error showing statistics")



class Keyboard:

    @staticmethod
    def start_keyboard():
        """Returns the start menu keyboard"""
        return [
            [Button.inline("Account Management", 'account_management')],
                [
                Button.inline("Individual", 'individual_keyboard'),
                Button.inline("Bulk", 'bulk_operations')
                ],
            [Button.inline("Monitor Mode", 'monitor_mode')],
            [Button.inline("Report", 'report')]
                ]

    @staticmethod
    def monitor_keyboard():
        """Returns the monitor mode keyboard"""
        return [
            [
                Button.inline('Add Keyword', b'add_keyword'),
                Button.inline('Remove Keyword', b'remove_keyword')
            ],
            [
                Button.inline('Ignore User', b'ignore_user'),
                Button.inline('Remove Ignore', b'remove_ignore_user')
            ],
            [Button.inline("Update Groups", b'update_groups')],
            [
                Button.inline('Show Groups', b'show_groups'),
                Button.inline('Show Keyword', b'Show_keyword')
            ],
            [Button.inline("Show Ignores", b'show_ignores')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def bulk_keyboard():
        """Returns a keyboard with action buttons like like, join, block, message, comment"""
        return [
            [Button.inline('Reaction', 'bulk_reaction')],
            [Button.inline('Poll', 'bulk_poll')],
            [Button.inline('Join', 'bulk_join')],
            [Button.inline('Block', 'bulk_block')],
            [Button.inline('Send pv', 'bulk_send_pv')],
            [Button.inline('Comment', 'bulk_comment')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def account_management_keyboard():
        """Returns the keyboard for account management"""
        return [
            [Button.inline('Add Account', 'add_account')],
            [Button.inline('List Accounts', 'list_accounts')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def channel_message_keyboard(message_link, sender_id):
        """Returns a keyboard with a 'View Message' URL button and 'Ignore' inline button"""
        return [
            [Button.url("View Message", url=message_link)],
            [Button.inline("❌Ignore❌", data=f"ignore_{sender_id}")]
        ]
    
    @staticmethod
    def toggle_and_delete_keyboard(status, session):
        """Returns a keyboard with 'Disable/Enable' and 'Delete' buttons"""
        return [
            [
                Button.inline(
                    "❌ Disable" if status == "🟢 Active" else "✅ Enable", 
                    data=f"toggle_{session}"
                ),
                Button.inline("🗑 Delete", data=f"delete_{session}")
            ]
        ]

    @staticmethod
    def individual_keyboard():
        """Returns the keyboard for individual operations"""
        return [
            [Button.inline("Send PV", 'send_pv')],
            [Button.inline("Join", 'join')],
            [Button.inline("Left", 'left')],
            [Button.inline("Comment", 'comment')],
            [Button.inline("Exit", 'exit')]

        ]

    @staticmethod
    def report_keyboard():
        """Returns the keyboard for report"""
        return [
            [Button.inline("Show Stats", 'show_stats')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    async def show_keyboard(keyboard_name, event=None):
        """Dynamically returns and shows the requested keyboard based on its name"""
        keyboards = {
            'start': Keyboard.start_keyboard(),
            'monitor': Keyboard.monitor_keyboard(),
            'bulk': Keyboard.bulk_keyboard(),
            'account_management': Keyboard.account_management_keyboard(),
            'channel_message': Keyboard.channel_message_keyboard,
            'toggle_and_delete': Keyboard.toggle_and_delete_keyboard,
            'individual_keyboard': Keyboard.individual_keyboard(),
            'report': Keyboard.report_keyboard(),
            'bulk_reaction' : Actions.prompt_group_action
            
        }
    

        # Return the keyboard if it exists
        keyboard = keyboards.get(keyboard_name, None)
        
        if keyboard:
            if event:
                # Clear the previous keyboard
                await event.edit("Please choose an option:", buttons=keyboard)
            return keyboard
        else:
            if event:
                return event.respond("Sorry, the requested keyboard is not available.")
            return None
        










            [Button.inline('Reaction', 'bulk_reaction')],
            [Button.inline('Poll', 'bulk_poll')],
            [Button.inline('Join', 'bulk_join')],
            [Button.inline('Block', 'bulk_block')],
            [Button.inline('Send pv', 'bulk_send_pv')],
            [Button.inline('Comment', 'bulk_comment')]