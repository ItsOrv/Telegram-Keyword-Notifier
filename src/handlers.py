import os
import logging
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from src.config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID, ADMIN_ID ,CLIENTS_JSON_PATH, RATE_LIMIT_SLEEP, GROUPS_BATCH_SIZE, GROUPS_UPDATE_SLEEP
from src.client import SessionManager ,AccountHandler
from src.keyboards import Keyboard
from src.actions import Actions
from src.validation import InputValidator
from src.utils import (
    get_session_name, cleanup_conversation_state, is_session_revoked_error,
    check_admin_access, is_bot_message, prompt_for_input,
    cleanup_handlers_and_state
) 

# Setting up the logger
logger = logging.getLogger(__name__)

REACTION_BUTTONS = frozenset({
    'reaction_thumbsup', 'reaction_heart', 'reaction_laugh',
    'reaction_wow', 'reaction_sad', 'reaction_angry',
})
INDIVIDUAL_ACTIONS = ('reaction', 'send_pv', 'join', 'left', 'block', 'comment')
BULK_ACTIONS = ('reaction', 'poll', 'join', 'leave', 'block', 'comment', 'send_pv')
UNKNOWN_COMMAND = "Command not recognized. Please try again."

CONVERSATION_ROUTES = {
    'phone_number_handler': 'account_handler',
    'code_handler': 'account_handler',
    'password_handler': 'account_handler',
    'ignore_user_handler': 'keyword_handler',
    'delete_ignore_user_handler': 'keyword_handler',
    'add_keyword_handler': 'keyword_handler',
    'remove_keyword_handler': 'keyword_handler',
    'reaction_link_handler': 'actions',
    'poll_link_handler': 'actions',
    'poll_option_handler': 'actions',
    'join_link_handler': 'actions',
    'left_link_handler': 'actions',
    'block_user_handler': 'actions',
    'send_pv_user_handler': 'actions',
    'send_pv_message_handler': 'actions',
    'bulk_send_pv_account_count_handler': 'actions',
    'bulk_send_pv_user_handler': 'actions',
    'bulk_send_pv_message_handler': 'actions',
    'comment_link_handler': 'actions',
    'comment_text_handler': 'actions',
    'bulk_join_link_handler': 'actions',
    'bulk_leave_link_handler': 'actions',
    'bulk_block_user_handler': 'actions',
}


# Constants

def is_callback_event(event):
    """Check if an event is a callback query event"""
    if isinstance(event, events.CallbackQuery.Event):
        return True
    # For testing: callback events have 'data' attribute, message events have 'message' attribute
    # Check if 'data' exists and 'message' is None or doesn't exist
    has_data = hasattr(event, 'data') and getattr(event, 'data', None) is not None
    message_attr = getattr(event, 'message', None)
    # Message is None means it's a callback event, message exists means it's a message event
    has_message = message_attr is not None
    return has_data and not has_message


class CommandHandler:
    def __init__(self, tbot):
        self.bot = tbot

    async def start_command(self, event):
        """
        Handle /start command.
        
        Displays the main menu keyboard to authorized admin users.
        
        Args:
            event: Telegram NewMessage event
        """
        logger.info(f"Start command received from user {event.sender_id}")
        try:
            # Validate ADMIN_ID before comparison
            try:
                from src.utils import validate_admin_id
                validated_admin_id = validate_admin_id(ADMIN_ID)
            except ValueError as e:
                logger.error(f"Invalid ADMIN_ID configuration: {e}")
                await event.respond("Bot configuration error. Please contact administrator.")
                return
            
            if event.sender_id != validated_admin_id:
                logger.warning(f"Unauthorized /start from {event.sender_id}")
                await event.respond("You are not the admin")
                return

            # /start resets any in-progress conversation so the next message is a
            # fresh interaction (other entry points already do this).
            await cleanup_conversation_state(self.bot, event.chat_id)

            buttons = Keyboard.start_keyboard()
            await event.respond(
                "Telegram Management Bot\n\n",
                buttons=buttons
            )

        except Exception as e:
            logger.error(f"Error in start_command: {e}", exc_info=True)
            try:
                await event.respond("Error showing menu. Please try again.")
            except Exception as e2:
                logger.error(f"Error sending error message: {e2}")

class KeywordHandler:
    def __init__(self, tbot):
        self.tbot = tbot

    async def add_keyword_handler(self, event):
        """Add a keyword to monitor"""
        logger.info("add_keyword_handler in KeywordHandler")
        try:
            if is_callback_event(event):
                await prompt_for_input(
                    self.tbot, event,
                    "Please enter the keyword you want to add.",
                    'add_keyword_handler'
                )
                return

            keyword = str(event.message.text.strip())
            
            # Validate keyword
            is_valid, error_msg = InputValidator.validate_keyword(keyword)
            if not is_valid:
                await event.respond(f"{error_msg}")
                return
            
            if keyword not in self.tbot.config['KEYWORDS']:
                self.tbot.config['KEYWORDS'].append(keyword)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"Keyword '{keyword}' added successfully")
            else:
                await event.respond(f"Keyword '{keyword}' already exists")

            keywords = ', '.join(str(k) for k in self.tbot.config['KEYWORDS'])
            await event.respond(f"Current keywords: {keywords}")
            
            # Cleanup conversation state
            await cleanup_conversation_state(self.tbot, event.chat_id)

        except Exception as e:
            logger.error(f"Error adding keyword: {e}")
            await event.respond("Error adding keyword")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def remove_keyword_handler(self, event):
        """Remove a keyword from monitoring"""
        logger.info("remove_keyword_handler in KeywordHandler")
        try:
            if is_callback_event(event):
                await prompt_for_input(
                    self.tbot, event,
                    "Please enter the keyword you want to remove.",
                    'remove_keyword_handler'
                )
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
            
            # Cleanup conversation state
            await cleanup_conversation_state(self.tbot, event.chat_id)

        except Exception as e:
            logger.error(f"Error removing keyword: {e}")
            await event.respond("Error removing keyword")
            await cleanup_conversation_state(self.tbot, event.chat_id)

    async def ignore_user_handler(self, event):
        """Ignore a user from further interaction"""
        logger.info("ignore_user_handler in KeywordHandler")
        try:
            if is_callback_event(event):
                await prompt_for_input(
                    self.tbot, event,
                    "Please enter the user ID you want to ignore.",
                    'ignore_user_handler'
                )
                return

            # Validate and parse user ID
            is_valid, error_msg, user_id = InputValidator.validate_user_id(event.message.text.strip())
            if not is_valid:
                await event.respond(f"{error_msg}")
                return
            
            if user_id not in self.tbot.config['IGNORE_USERS']:
                self.tbot.config['IGNORE_USERS'].append(user_id)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"User ID {user_id} is now ignored")
            else:
                await event.respond(f"User ID {user_id} is already ignored")

            ignored_users = ', '.join(str(u) for u in self.tbot.config['IGNORE_USERS'])
            await event.respond(f"Ignored users: {ignored_users}")
            
            # Cleanup conversation state
            await cleanup_conversation_state(self.tbot, event.chat_id)

        except Exception as e:
            logger.error(f"Error ignoring user: {e}")
            await event.respond("Error ignoring user")
            await cleanup_conversation_state(self.tbot, event.chat_id)

    async def delete_ignore_user_handler(self, event):
        """Remove a user from the ignore list"""
        logger.info("delete_ignore_user_handler in KeywordHandler")
        try:
            if is_callback_event(event):
                await prompt_for_input(
                    self.tbot, event,
                    "Please enter the user ID you want to remove from the ignore list.",
                    'delete_ignore_user_handler'
                )
                return

            # Validate and parse user ID
            is_valid, error_msg, user_id = InputValidator.validate_user_id(event.message.text.strip())
            if not is_valid:
                await event.respond(f"{error_msg}")
                return
            
            if user_id in self.tbot.config['IGNORE_USERS']:
                self.tbot.config['IGNORE_USERS'].remove(user_id)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"User ID {user_id} is no longer ignored")
            else:
                await event.respond(f"User ID {user_id} not found in ignored list")

            ignored_users = ', '.join(str(u) for u in self.tbot.config['IGNORE_USERS'])
            await event.respond(f"Ignored users: {ignored_users}")
            
            # Cleanup conversation state
            await cleanup_conversation_state(self.tbot, event.chat_id)

        except Exception as e:
            logger.error(f"Error deleting ignored user: {e}")
            await event.respond("Error removing user from ignore list")
            await cleanup_conversation_state(self.tbot, event.chat_id)

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
        self.actions = Actions(tbot)

    async def message_handler(self, event):
        """Handle incoming messages based on conversation state"""
        logger.info(f"message_handler in MessageHandler - message: {event.message.text}")

        # Skip messages from the bot itself
        if is_bot_message(event, BOT_TOKEN):
            logger.debug(f"Ignoring message from bot itself")
            return False

        # Skip if this is a command (should be handled by command handler)
        if event.message.text and event.message.text.startswith('/'):
            logger.debug(f"Skipping command message: {event.message.text}")
            return False

        # Allow admin user to continue conversations
        try:
            admin_id = int(ADMIN_ID) if isinstance(ADMIN_ID, str) else ADMIN_ID
            if not await check_admin_access(event, admin_id):
                logger.warning(f"Non-admin message from {event.sender_id}: {(event.message.text or '')[:50]}...")
                await event.respond("You are not the admin")
                return False
        except (ValueError, TypeError):
            # If ADMIN_ID is not valid, skip admin check
            pass

        # Use lock when reading conversation state
        async with self.tbot._conversations_lock:
            handler_name = self.tbot._conversations.get(event.chat_id)
        
        if handler_name:
            owner_name = CONVERSATION_ROUTES.get(handler_name)
            if owner_name:
                await getattr(getattr(self, owner_name), handler_name)(event)
                return True

        return False

class StatsHandler:
    def __init__(self, tbot):
        self.tbot = tbot

    async def show_stats(self, event):
        """Show bot statistics"""
        logger.info("show_stats in StatsHandler")
        try:
            async with self.tbot.active_clients_lock:
                active_count = len(self.tbot.active_clients)
            
            stats = {
                "Total Accounts": len(self.tbot.config['clients']),
                "Active Accounts": active_count,
                "Keywords": len(self.tbot.config['KEYWORDS']),
                "Ignored Users": len(self.tbot.config['IGNORE_USERS'])
            }

            text = "Bot Statistics\n\n"
            for key, value in stats.items():
                text += f"• {key}: {value}\n"

            await Keyboard.edit_or_respond(event, text, buttons=Keyboard.back_button())

        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await Keyboard.edit_or_respond(event, "Error showing statistics", buttons=Keyboard.back_button())

    async def show_groups(self, event):
        """Show all groups for all clients"""
        logger.info("show_groups in StatsHandler")
        try:
            clients_data = self.tbot.config.get('clients', {})
            
            if not isinstance(clients_data, dict) or not clients_data:
                await Keyboard.edit_or_respond(event, "No groups found. Please run 'Update Groups' first.", buttons=Keyboard.back_button())
                return
            
            text = "Groups per Account:\n\n"
            total_groups = 0
            
            # Get active clients snapshot to filter revoked sessions
            async with self.tbot.active_clients_lock:
                active_sessions = set(self.tbot.active_clients.keys())
            
            for session, groups in clients_data.items():
                # Skip revoked sessions (in config but not in active_clients and not in inactive_accounts)
                if session not in active_sessions:
                    # Check if it's in inactive_accounts
                    if 'inactive_accounts' not in self.tbot.config or session not in self.tbot.config['inactive_accounts']:
                        # Session is in config but not active and not in inactive_accounts - likely revoked, skip it
                        logger.debug(f"Skipping potentially revoked session {session} in show_groups")
                        continue
                    else:
                        # Check if reason indicates revoked session
                        inactive_reason = self.tbot.config['inactive_accounts'][session].get('reason', '').lower()
                        if 'revoked' in inactive_reason or 'auth' in inactive_reason or 'session' in inactive_reason:
                            logger.debug(f"Skipping revoked session {session} in show_groups")
                            continue
                
                phone = session.replace('.session', '') if session else 'Unknown'
                groups_count = len(groups) if isinstance(groups, list) else 0
                total_groups += groups_count
                text += f"• {phone}: {groups_count} groups\n"
            
            text += f"\nTotal: {total_groups} groups"
            await Keyboard.edit_or_respond(event, text, buttons=Keyboard.back_button())

        except Exception as e:
            logger.error(f"Error showing groups: {e}")
            await Keyboard.edit_or_respond(event, "Error showing groups", buttons=Keyboard.back_button())

    async def show_keywords(self, event):
        """Show all configured keywords"""
        logger.info("show_keywords in StatsHandler")
        try:
            keywords = self.tbot.config.get('KEYWORDS', [])
            
            if not keywords:
                await Keyboard.edit_or_respond(event, "No keywords configured yet.", buttons=Keyboard.back_button())
                return

            text = "Configured Keywords:\n\n"
            for idx, keyword in enumerate(keywords, 1):
                text += f"{idx}. {keyword}\n"

            await Keyboard.edit_or_respond(event, text, buttons=Keyboard.back_button())

        except Exception as e:
            logger.error(f"Error showing keywords: {e}")
            await Keyboard.edit_or_respond(event, "Error showing keywords", buttons=Keyboard.back_button())

    async def show_ignores(self, event):
        """Show all ignored users"""
        logger.info("show_ignores in StatsHandler")
        try:
            ignored_users = self.tbot.config.get('IGNORE_USERS', [])
            
            if not ignored_users:
                await Keyboard.edit_or_respond(event, "No users are currently ignored.", buttons=Keyboard.back_button())
                return

            text = "Ignored Users:\n\n"
            for idx, user_id in enumerate(ignored_users, 1):
                text += f"{idx}. User ID: {user_id}\n"

            await Keyboard.edit_or_respond(event, text, buttons=Keyboard.back_button())

        except Exception as e:
            logger.error(f"Error showing ignored users: {e}")
            await Keyboard.edit_or_respond(event, "Error showing ignored users", buttons=Keyboard.back_button())


class CallbackHandler:
    def __init__(self, tbot):
        self.tbot = tbot
        self.account_handler = AccountHandler(self.tbot)
        self.keyword_handler = KeywordHandler(self.tbot)
        self.stats_handler = StatsHandler(self.tbot)
        self.actions = Actions(self.tbot)

        self.callback_actions = {
            'add_account': self.account_handler.add_account,
            'list_accounts': self.account_handler.show_accounts,
            'check_report_status': self.account_handler.check_all_accounts_report_status,
            'inactive_accounts': self.handle_inactive_accounts,
            'update_groups': self.account_handler.update_groups,
            'add_keyword': self.keyword_handler.add_keyword_handler,
            'remove_keyword': self.keyword_handler.remove_keyword_handler,
            'ignore_user': self.keyword_handler.ignore_user_handler,
            'remove_ignore_user': self.keyword_handler.delete_ignore_user_handler,
            'show_stats': self.stats_handler.show_stats,
            'show_groups': self.stats_handler.show_groups,
            'show_keyword': self.stats_handler.show_keywords,
            'show_ignores': self.stats_handler.show_ignores,
            'monitor_mode': self.show_monitor_keyboard,
            'account_management': self.show_account_management_keyboard,
            'bulk_operations': self.show_bulk_operations_keyboard,
            'individual_keyboard': self.show_individual_keyboard,
            'report': self.show_report_keyboard,
            'exit': self.show_start_keyboard,
            'back_to_start': self.handle_back_to_start,
            # Bulk operations
            'bulk_reaction': self.handle_bulk_reaction,
            'bulk_poll': self.handle_bulk_poll,
            'bulk_join': self.handle_bulk_join,
            'bulk_leave': self.handle_bulk_leave,
            'bulk_block': self.handle_bulk_block,
            'bulk_send_pv': self.handle_bulk_send_pv,
            'bulk_comment': self.handle_bulk_comment,
            # Individual operations
            'reaction': self.handle_individual_reaction,
            'send_pv': self.handle_individual_send_pv,
            'join': self.handle_individual_join,
            'left': self.handle_individual_left,
            'block': self.handle_individual_block,
            'comment': self.handle_individual_comment,
        }

    async def show_start_keyboard(self, event):
        """Handles the start keyboard display"""
        # Clean up any active conversations when returning to start
        await cleanup_conversation_state(self.tbot, event.chat_id)
        await Keyboard.show_keyboard('start', event, self.tbot)

    async def handle_back_to_start(self, event):
        """Handle back to start navigation with cleanup"""
        # show_start_keyboard cleans up conversation state and edits the current
        # message in place into the main menu (no stale message left behind).
        await self.show_start_keyboard(event)

    async def show_monitor_keyboard(self, event):
        """Handles the monitor mode keyboard display"""
        await Keyboard.show_keyboard('monitor', event, self.tbot)

    async def show_account_management_keyboard(self, event):
        """Handles the account management keyboard display"""
        await Keyboard.show_keyboard('account_management', event, self.tbot)

    async def show_bulk_operations_keyboard(self, event):
        """Handles the bulk operations keyboard display"""
        await Keyboard.show_keyboard('bulk', event, self.tbot)

    async def show_individual_keyboard(self, event):
        """Handles the individual operations keyboard display"""
        await Keyboard.show_keyboard('individual_keyboard', event, self.tbot)

    async def show_report_keyboard(self, event):
        """Handles the report keyboard display"""
        keyboard = Keyboard.report_keyboard()
        try:
            if hasattr(event, 'answer'):
                await event.answer()
            await event.edit("Report Status\n\nPlease select an option:", buttons=keyboard)
        except Exception as e:
            logger.error(f"Error showing report keyboard: {e}")
            await event.respond("Report Status\n\nPlease select an option:", buttons=keyboard)

    async def handle_bulk_reaction(self, event):
        """
        Handle bulk reaction operation.
        
        Args:
            event: Telegram CallbackQuery event
        """
        await self.actions.prompt_group_action(event, 'reaction')

    async def handle_bulk_poll(self, event):
        """
        Handle bulk poll operation.
        
        Args:
            event: Telegram CallbackQuery event
        """
        async with self.tbot.active_clients_lock:
            total_accounts = len(self.tbot.active_clients)
        if total_accounts == 0:
            await event.respond("No accounts available for this operation.")
            return
        await self.actions.bulk_poll(event, total_accounts)

    async def handle_bulk_join(self, event):
        """
        Handle bulk join operation.
        
        Args:
            event: Telegram CallbackQuery event
        """
        await self.actions.prompt_group_action(event, 'join')

    async def handle_bulk_leave(self, event):
        """
        Handle bulk leave operation.
        
        Args:
            event: Telegram CallbackQuery event
        """
        await self.actions.prompt_group_action(event, 'leave')

    async def handle_bulk_block(self, event):
        """
        Handle bulk block operation.
        
        Args:
            event: Telegram CallbackQuery event
        """
        await self.actions.prompt_group_action(event, 'block')

    async def handle_bulk_send_pv(self, event):
        """Handle bulk send_pv operation"""
        logger.info("handle_bulk_send_pv in CallbackHandler")

        # Answer the callback query first
        try:
            await event.answer()
            logger.info("Callback query answered")
        except Exception as e:
            logger.warning(f"Failed to answer callback: {e}")

        async with self.tbot.active_clients_lock:
            total_accounts = len(self.tbot.active_clients)
        logger.info(f"Total accounts available: {total_accounts}")
        if total_accounts == 0:
            await event.respond("No accounts available for this operation.")
            return

        # Ask user to specify how many accounts they want to use
        message = f"You currently have {total_accounts} accounts available.\n\nHow many accounts do you want to use for this task?\n\nPlease send a number between 1 and {total_accounts}:"
        logger.info(f"Sending message to user: {message[:50]}...")
        try:
            await event.respond(message)
            logger.info("Message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return

        # Set up conversation to receive the number of accounts
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'bulk_send_pv_account_count_handler'
        logger.info("Conversation state set to bulk_send_pv_account_count_handler")

    async def handle_bulk_comment(self, event):
        """Handle bulk comment operation"""
        logger.info("handle_bulk_comment in CallbackHandler")
        await self.actions.prompt_group_action(event, 'comment')

    # Individual operation handlers
    async def handle_individual_reaction(self, event):
        """Handle individual reaction operation"""
        logger.info("handle_individual_reaction in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'reaction')
    
    async def handle_individual_send_pv(self, event):
        """Handle individual send_pv operation"""
        logger.info("handle_individual_send_pv in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'send_pv')

    async def handle_individual_join(self, event):
        """Handle individual join operation"""
        logger.info("handle_individual_join in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'join')

    async def handle_individual_left(self, event):
        """Handle individual left operation"""
        logger.info("handle_individual_left in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'left')

    async def handle_individual_block(self, event):
        """Handle individual block operation"""
        logger.info("handle_individual_block in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'block')

    async def handle_individual_comment(self, event):
        """Handle individual comment operation"""
        logger.info("handle_individual_comment in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'comment')

    async def handle_inactive_accounts(self, event):
        """
        Handle inactive accounts display.
        
        Args:
            event: Telegram CallbackQuery event
        """
        if hasattr(self.tbot, 'client_manager') and self.tbot.client_manager:
            await self.tbot.client_manager.show_inactive_accounts(event)
        else:
            await event.respond("Client manager not initialized. Please restart the bot.")

    async def _answer_callback(self, event):
        try:
            await event.answer()
        except Exception as e:
            logger.warning(f"Error answering callback query: {e}")

    async def _callback_sender_is_admin(self, event) -> bool:
        try:
            admin_id = int(ADMIN_ID) if isinstance(ADMIN_ID, str) else ADMIN_ID
        except (ValueError, TypeError):
            logger.warning(f"Invalid ADMIN_ID: {ADMIN_ID}, skipping admin check")
            return True
        if admin_id != 0 and event.sender_id != admin_id:
            await event.respond("You are not the admin")
            return False
        return True

    @staticmethod
    def _split_action(data: str):
        """Split callback data into (action, suffix); 'send_pv' contains an underscore."""
        parts = data.split('_')
        if len(parts) >= 3 and parts[0] == 'send' and parts[1] == 'pv':
            return 'send_pv', '_'.join(parts[2:])
        return parts[0], '_'.join(parts[1:])

    async def _handle_ignore(self, event, data):
        parts = data.split('_')
        if len(parts) == 2 and parts[1].isdigit():
            await self.keyword_handler.ignore_user(int(parts[1]), event)
        else:
            logger.error(f"Invalid user ID in callback data: {data}")
            await event.respond("Invalid user ID.")

    async def _handle_toggle(self, event, data):
        await self.account_handler.toggle_client(data.replace('toggle_', ''), event)

    async def _handle_delete(self, event, data):
        session = data.replace('delete_', '')
        try:
            if getattr(self.tbot, 'client_manager', None):
                await self.tbot.client_manager.delete_session(session)
                await event.respond(f"Account {session} deleted successfully.")
            else:
                await event.respond("Client manager not initialized. Please restart the bot.")
        except Exception as e:
            logger.error(f"Error deleting session {session}: {e}")
            await event.respond(f"Error deleting account {session}: {str(e)}")

    async def _handle_account_or_bulk(self, event, data):
        """Route callbacks like 'reaction_3' (bulk) or 'reaction_98912...' (one account)."""
        action_name, suffix = self._split_action(data)

        # Check the suffix against active accounts first: session keys are phone
        # numbers, so isdigit() alone would read an account pick as a bulk count.
        async with self.tbot.active_clients_lock:
            account = self.tbot.active_clients.get(suffix)
            active_count = len(self.tbot.active_clients)

        if account is not None and action_name in INDIVIDUAL_ACTIONS:
            await getattr(self.actions, action_name)(account, event)
        elif (suffix.isdigit() and action_name in BULK_ACTIONS
              and int(suffix) <= active_count):
            # The count bound stops a vanished digit-only session key from being
            # read as a huge bulk count and fanning out to every account.
            await self.actions.handle_group_action(event, action_name, int(suffix))
        elif action_name in INDIVIDUAL_ACTIONS:
            await event.respond(f"Account {suffix} not found.")
        else:
            await self._fallback(event, data)

    async def _fallback(self, event, data):
        action = self.callback_actions.get(data)
        if action:
            await action(event)
        else:
            logger.warning(f"No handler found for callback data: {data}")
            await event.respond(UNKNOWN_COMMAND)

    async def _route_callback(self, event, data):
        if data == 'cancel':
            await cleanup_conversation_state(self.tbot, event.chat_id)
            # Replace the cancelled prompt in place rather than leaving it behind.
            await self.show_start_keyboard(event)
        elif data == 'request_phone_number':
            await prompt_for_input(
                self.tbot, event,
                "Please enter your phone number:",
                'phone_number_handler'
            )
        elif data in REACTION_BUTTONS:
            await self.actions.reaction_select_handler(event)
        elif data in self.callback_actions:
            await self.callback_actions[data](event)
        elif data.startswith('ignore_'):
            await self._handle_ignore(event, data)
        elif data.startswith('toggle_'):
            await self._handle_toggle(event, data)
        elif data.startswith('delete_'):
            await self._handle_delete(event, data)
        elif '_' in data:
            await self._handle_account_or_bulk(event, data)
        else:
            await self._fallback(event, data)

    async def callback_handler(self, event):
        """Handle callback queries"""
        logger.info("callback_handler in CallbackHandler")
        try:
            if is_bot_message(event, BOT_TOKEN):
                logger.debug(f"Ignoring callback from bot itself")
                return

            await self._answer_callback(event)
            if not await self._callback_sender_is_admin(event):
                return

            await self._route_callback(event, event.data.decode())

        except Exception as e:
            logger.error(f"Error in callback_handler: {e}", exc_info=True)
            try:
                await event.respond("Error processing request. Please try again.")
            except Exception as e2:
                logger.error(f"Error sending error message: {e2}")
