import os
import logging
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from src.Config import API_ID, API_HASH, CHANNEL_ID
from src.Client import ClientManager
from asyncio.log import logger

# Setting up the logger
logger = logging.getLogger(__name__)


class AccountHandler:
    """
    Handles all account-related operations for the Telegram bot.
    Manages account creation, authentication, and message processing.
    """
    
    def __init__(self, tbot):
        """
        Initialize AccountHandler with bot instance.
        
        Args:
            bot: Bot instance containing configuration and client management
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
        try:
            chat_id = event.chat_id
            await self.tbot.tbot.send_message(chat_id, "Please enter your phone number:")
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
        try:
            phone_number = event.message.text.strip()
            chat_id = event.chat_id

            client = TelegramClient(phone_number, self.tbot.api_id, self.tbot.api_hash)
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
        try:
            code = event.message.text.strip()
            chat_id = event.chat_id
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
        try:
            password = event.message.text.strip()
            chat_id = event.chat_id
            client = self.tbot.handlers.get('temp_client')
            phone_number = self.tbot.handlers.get('temp_phone')

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
            session_name = f"{phone_number}_session"
            client.session.save()

            self.tbot.config['clients'].append({
                "phone_number": phone_number,
                "session": session_name,
                "groups": [],
                "added_date": datetime.now().isoformat(),
                "disabled": False
            })
            self.tbot.config_manager.save_config()

            self.tbot.active_clients[session_name] = client
            client.add_event_handler(
                self.process_message,
                events.NewMessage()
            )

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
            if 'temp_client' in self.tbot.handlers:
                del self.tbot.handlers['temp_client']
            if 'temp_phone' in self.tbot.handlers:
                del self.tbot.handlers['temp_phone']
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

            # Initialize JSON structure
            json_data = {
                "TARGET_GROUPS": [],
                "KEYWORDS": [],
                "IGNORE_USERS": [],
                "clients": {}
            }

            # Load existing data
            if os.path.exists("clients.json"):
                try:
                    with open("clients.json", "r", encoding='utf-8') as json_file:
                        loaded_data = json.loads(json_file.read())
                        json_data.update(loaded_data)
                        if isinstance(json_data["clients"], list):
                            json_data["clients"] = {session: [] for session in json_data["clients"]}
                    logger.info("Loaded existing client data from clients.json.")
                except json.JSONDecodeError as e:
                    logger.error("Error decoding clients.json.", exc_info=True)

            # Process each client
            for session_name, client in self.tbot.active_clients.items():
                try:
                    logger.info(f"Processing client: {session_name}")
                    group_ids = set()

                    try:
                        async for dialog in client.iter_dialogs(limit=None):
                            try:
                                if isinstance(dialog.entity, (Chat, Channel)) and not (
                                    isinstance(dialog.entity, Channel) and dialog.entity.broadcast
                                ):
                                    group_ids.add(dialog.entity.id)

                                if len(group_ids) % 50 == 0:
                                    await asyncio.sleep(2)  # Rate limiting protection

                            except Exception as e:
                                logger.error(f"Error processing dialog for client {session_name}.", exc_info=True)
                                continue

                            if len(group_ids) % 20 == 0:
                                await status_message.edit(f"Found {len(group_ids)} groups for {session_name}...")

                    except FloodWaitError as e:
                        wait_time = e.seconds
                        logger.warning(f"FloodWaitError: Sleeping for {wait_time} seconds for client {session_name}.")
                        await status_message.edit(f"Rate limited. Waiting for {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue

                    except Exception as e:
                        logger.error(f"Error iterating dialogs for client {session_name}.", exc_info=True)
                        await status_message.edit(f"Error processing {session_name}: {str(e)}")
                        continue

                    groups_per_client[session_name] = list(group_ids)
                    logger.info(f"Found {len(group_ids)} groups for client {session_name}.")
                    await status_message.edit(f"Found {len(group_ids)} groups for {session_name}.")
                    await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"Unexpected error while processing client {session_name}.", exc_info=True)
                    continue

            # Update JSON data
            for session_name, group_ids in groups_per_client.items():
                if session_name in json_data["clients"]:
                    existing_groups = json_data["clients"][session_name]
                    if not isinstance(existing_groups, list):
                        existing_groups = []
                    json_data["clients"][session_name] = list(set(existing_groups + group_ids))
                else:
                    json_data["clients"][session_name] = group_ids

            # Save updated data
            with open("clients.json", "w", encoding='utf-8') as json_file:
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

        # TODO: Implement message queuing system
        # TODO: Add message deduplication
        # TODO: Implement message filtering optimization
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
                    return

                if sender.id in self.tbot.config['IGNORE_USERS']:
                    logger.info(f"Message from ignored user {sender.id}. Skipping.")
                    return

                if not any(keyword.lower() in message.lower() for keyword in self.tbot.config['KEYWORDS']):
                    logger.debug("Message does not contain any configured keywords. Skipping.")
                    return

                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', 'Unknown Chat')
                logger.info(f"Processing message from chat: {chat_title}")

                # Format message for forwarding
                text = (
                    f"\u2022 User: {getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}\n"
                    f"\u2022 User ID: `{sender.id}`\n"
                    f"\u2022 Chat: {chat_title}\n\n"
                    f"\u2022 Message:\n{message}\n"
                )

                # Generate message link
                if hasattr(chat, 'username') and chat.username:
                    message_link = f"https://t.me/{chat.username}/{event.id}"
                else:
                    chat_id = str(event.chat_id).replace('-100', '', 1)
                    message_link = f"https://t.me/c/{chat_id}/{event.id}"

                buttons = [
                    [Button.url("View Message", url=message_link)],
                    [Button.inline("\ud83d\udeabIgnore\ud83d\udeab", data=f"ignore_{sender.id}")]
                ]

                await self.tbot.tbot.send_message(
                    CHANNEL_ID,
                    text,
                    buttons=buttons,
                    link_preview=False
                )

                logger.info(f"Forwarded message from user {sender.id} in chat {chat_title}.")

            except Exception as e:
                logger.error("Error processing message.", exc_info=True)


    async def show_accounts(self, event):
        """
        Display all registered accounts with their current status and controls.

        Args:
            event: Telegram event triggering the account display

        Returns:
            None. Sends interactive messages to the chat with account information
            and control buttons.

        """
        logger.info("Executing show_accounts method in AccountHandler")

        try:
            # Retrieve client data with fallback to an empty dictionary
            clients_data = self.tbot.config.get('clients', {})

            # Log client data retrieval
            logger.debug(f"Retrieved clients data: {clients_data}")

            # Validate client data structure
            if not isinstance(clients_data, dict) or not clients_data:
                await event.respond("No accounts added yet.")
                logger.warning("No accounts found in the configuration.")
                return

            messages = []

            # Process each client account
            for session, groups in clients_data.items():
                try:
                    # Clean up phone number display
                    phone = session.replace('.session', '') if session else 'Unknown'
                    groups_count = len(groups)
                    status = "🟢 Active" if session in self.tbot.active_clients else "🔴 Inactive"

                    logger.debug(f"Processing account: {session}, Status: {status}, Groups: {groups_count}")

                    # Format account information message
                    text = (
                        f"• Phone: {phone}\n"
                        f"• Groups: {groups_count}\n"
                        f"• Status: {status}\n"
                    )

                    # Create interactive control buttons
                    buttons = [
                        [
                            Button.inline(
                                "❌ Disable" if status == "🟢 Active" else "✅ Enable", 
                                data=f"toggle_{session}"
                            ),
                            Button.inline("🗑 Delete", data=f"delete_{session}")
                        ]
                    ]

                    messages.append((text, buttons))
                except Exception as e:
                    logger.error(f"Error processing account {session}: {e}", exc_info=True)

            # Send each account as a separate message with its controls
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
            # Validate session existence
            if session not in self.tbot.config['clients']:
                logger.warning(f"Session {session} not found in clients.")
                await event.respond("Account not found.")
                return

            currently_active = session in self.tbot.active_clients
            logger.info(f"Current status for {session}: {'Active' if currently_active else 'Inactive'}")

            if currently_active:
                # Handle client disable
                logger.info(f"Disabling client: {session}")
                client = self.tbot.active_clients[session]
                await client.disconnect()
                del self.tbot.active_clients[session]
                logger.info(f"Client {session} disabled successfully.")
                await event.respond(f"Account {session} disabled.")
            else:
                # Handle client enable
                logger.info(f"Enabling client: {session}")
                client = TelegramClient(session, API_ID, API_HASH)
                await client.start()
                self.tbot.active_clients[session] = client
                logger.info(f"Client {session} enabled successfully.")
                await event.respond(f"Account {session} enabled.")

            # Save updated configuration
            logger.info("Saving updated configuration.")
            self.tbot.config_manager.save_config()

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
            # Disconnect and remove active client if exists
            if session in self.tbot.active_clients:
                logger.info(f"Disconnecting active client: {session}")
                client = self.tbot.active_clients[session]
                await client.disconnect()
                del self.tbot.active_clients[session]
                logger.info(f"Client {session} disconnected and removed from active clients.")

            # Remove from configuration
            if session in self.tbot.config['clients']:
                logger.info(f"Removing session {session} from configuration.")
                del self.tbot.config['clients'][session]
                self.tbot.config_manager.save_config()

                # Clean up session file from disk
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


class CallbackHandler:
    def __init__(self, tbot):
        self.bot = tbot

    async def callback_handler(self, event):
        """Handle callback queries"""
        logger.info("callback_handler in CallbackHandler")
        try:
            data = event.data.decode()

            if data == 'add_account':
                logger.info("add_account in callback_handler in CallbackHandler")
                await AccountHandler(self.bot).add_account(event)
            elif data == 'request_phone_number':
                logger.info("request_phone_number in callback_handler in CallbackHandler")
                await event.respond("Please enter your phone number:")
                self.tbot._conversations[event.chat_id] = 'phone_number_handler'
            elif data == 'show_accounts':
                logger.info("show_accounts in callback_handler in CallbackHandler")
                await AccountHandler(self.bot).show_accounts(event)
            elif data.startswith('ignore_'):
                user_id = int(data.split('_')[1])
                await KeywordHandler(self.bot).ignore_user(user_id, event)
            elif data == 'update_groups':
                logger.info("update_groups in callback_handler in CallbackHandler")
                await AccountHandler(self.bot).update_groups(event)
            elif data.startswith('toggle_'):
                logger.info("toggle_ in callback_handler in CallbackHandler")
                session = data.replace('toggle_', '')
                await AccountHandler(self.bot).toggle_client(session, event)
            elif data.startswith('delete_'):
                logger.info("delete_ in callback_handler in CallbackHandler")
                session = data.replace('delete_', '')
                await AccountHandler(self.bot).delete_client(session, event)
            elif data == 'add_keyword':
                logger.info("add_keyword in callback_handler in CallbackHandler")
                await KeywordHandler(self.bot).add_keyword_handler(event)
            elif data == 'remove_keyword':
                logger.info("remove_keyword in callback_handler in CallbackHandler")
                await KeywordHandler(self.bot).remove_keyword_handler(event)
            elif data == 'ignore_user':
                logger.info("ignore_user in callback_handler in CallbackHandler")
                await KeywordHandler(self.bot).ignore_user_handler(event)
            elif data == 'remove_ignore_user':
                logger.info("remove_ignore_user in callback_handler in CallbackHandler")
                await KeywordHandler(self.bot).delete_ignore_user_handler(event)
            elif data == 'show_stats':
                logger.info("show_stats in callback_handler in CallbackHandler")
                await StatsHandler(self.bot).show_stats(event)
            
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
            buttons = [
                [Button.inline("Add Account", 'add_account')],
                [Button.inline("Show Accounts", b'show_accounts')],
                [Button.inline("Update Groups", b'update_groups')],
                [
                    Button.inline('Add Keyword', b'add_keyword'),
                    Button.inline('Remove Keyword', b'remove_keyword')
                ],
                [
                    Button.inline('Ignore User', b'ignore_user'),
                    Button.inline('Remove Ignore', b'remove_ignore_user')
                ],
                [Button.inline('Stats', b'show_stats')]
                ]

            await event.respond(
                "Telegram Management Bot\n\n",
                buttons=buttons
            )

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await event.respond("Error showing menu. Please try again.")


class KeywordHandler:
    def __init__(self, tbot):
        self.bot = tbot

    #PASS
    async def add_keyword_handler(self, event):
        """Add a keyword to monitor"""
        logger.info("add_keyword_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the keyword you want to add.")
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

    #PASS
    async def remove_keyword_handler(self, event):
        """Remove a keyword from monitoring"""
        logger.info("remove_keyword_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the keyword you want to remove.")
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

    #PASS
    async def ignore_user_handler(self, event):
        """Ignore a user from further interaction"""
        logger.info("ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the user ID you want to ignore.")
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

    #PASS
    async def delete_ignore_user_handler(self, event):
        """Remove a user from the ignore list"""
        logger.info("delete_ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the user ID you want to stop ignoring.")
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

    #PASS
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


