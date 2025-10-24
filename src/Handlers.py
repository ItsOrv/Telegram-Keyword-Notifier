import os
import logging
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from src.Config import API_ID, API_HASH, CHANNEL_ID, ADMIN_ID ,CLIENTS_JSON_PATH, RATE_LIMIT_SLEEP, GROUPS_BATCH_SIZE, GROUPS_UPDATE_SLEEP
from src.Client import SessionManager ,AccountHandler
from src.Keyboards import Keyboard
from src.actions import Actions
from src.Validation import InputValidator 

# Setting up the logger
logger = logging.getLogger(__name__)

# Constants


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
            
            # Validate keyword
            is_valid, error_msg = InputValidator.validate_keyword(keyword)
            if not is_valid:
                await event.respond(f"❌ {error_msg}")
                return
            
            if keyword not in self.tbot.config['KEYWORDS']:
                self.tbot.config['KEYWORDS'].append(keyword)
                self.tbot.config_manager.save_config(self.tbot.config)
                await event.respond(f"Keyword '{keyword}' added successfully")
            else:
                await event.respond(f"Keyword '{keyword}' already exists")

            keywords = ', '.join(str(k) for k in self.tbot.config['KEYWORDS'])
            await event.respond(f"📝 Current keywords: {keywords}")
            
            # Cleanup conversation state
            self.tbot._conversations.pop(event.chat_id, None)

        except Exception as e:
            logger.error(f"Error adding keyword: {e}")
            await event.respond("Error adding keyword")
            self.tbot._conversations.pop(event.chat_id, None)

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
            
            # Cleanup conversation state
            self.tbot._conversations.pop(event.chat_id, None)

        except Exception as e:
            logger.error(f"Error removing keyword: {e}")
            await event.respond("Error removing keyword")
            self.tbot._conversations.pop(event.chat_id, None)

    async def ignore_user_handler(self, event):
        """Ignore a user from further interaction"""
        logger.info("ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                buttons = [Button.inline("Cancel", b'cancel')]
                await event.respond("Please enter the user ID you want to ignore.", buttons=buttons)
                self.tbot._conversations[event.chat_id] = 'ignore_user_handler'
                return

            # Validate and parse user ID
            is_valid, error_msg, user_id = InputValidator.validate_user_id(event.message.text.strip())
            if not is_valid:
                await event.respond(f"❌ {error_msg}")
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
            self.tbot._conversations.pop(event.chat_id, None)

        except Exception as e:
            logger.error(f"Error ignoring user: {e}")
            await event.respond("Error ignoring user")
            self.tbot._conversations.pop(event.chat_id, None)

    async def delete_ignore_user_handler(self, event):
        """Remove a user from the ignore list"""
        logger.info("delete_ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                buttons = [Button.inline("Cancel", b'cancel')]
                await event.respond("Please enter the user ID you want to stop ignoring.", buttons=buttons)
                self.tbot._conversations[event.chat_id] = 'delete_ignore_user_handler'
                return

            # Validate and parse user ID
            is_valid, error_msg, user_id = InputValidator.validate_user_id(event.message.text.strip())
            if not is_valid:
                await event.respond(f"❌ {error_msg}")
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
            self.tbot._conversations.pop(event.chat_id, None)

        except Exception as e:
            logger.error(f"Error deleting ignored user: {e}")
            await event.respond("Error deleting ignored user")
            self.tbot._conversations.pop(event.chat_id, None)

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
        logger.info("message_handler in MessageHandler")

        if event.sender_id != int(ADMIN_ID):
            await event.respond("You are not the admin")
            return

        if event.chat_id in self.tbot._conversations:
            handler_name = self.tbot._conversations[event.chat_id]
            
            # Account handlers
            if handler_name == 'phone_number_handler':
                await self.account_handler.phone_number_handler(event)
                return True
            elif handler_name == 'code_handler':
                await self.account_handler.code_handler(event)
                return True
            elif handler_name == 'password_handler':
                await self.account_handler.password_handler(event)
                return True
            
            # Keyword handlers
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
            
            # Action handlers - Reaction
            elif handler_name == 'reaction_link_handler':
                await self.actions.reaction_link_handler(event)
                return True
            elif handler_name == 'reaction_count_handler':
                await self.actions.reaction_count_handler(event)
                return True
            
            # Action handlers - Poll
            elif handler_name == 'poll_link_handler':
                await self.actions.poll_link_handler(event)
                return True
            elif handler_name == 'poll_option_handler':
                await self.actions.poll_option_handler(event)
                return True
            
            # Action handlers - Join
            elif handler_name == 'join_link_handler':
                await self.actions.join_link_handler(event)
                return True
            
            # Action handlers - Left
            elif handler_name == 'left_link_handler':
                await self.actions.left_link_handler(event)
                return True
            
            # Action handlers - Block
            elif handler_name == 'block_user_handler':
                await self.actions.block_user_handler(event)
                return True
            
            # Action handlers - Send PV
            elif handler_name == 'send_pv_user_handler':
                await self.actions.send_pv_user_handler(event)
                return True
            elif handler_name == 'send_pv_message_handler':
                await self.actions.send_pv_message_handler(event)
                return True
            
            # Action handlers - Comment
            elif handler_name == 'comment_link_handler':
                await self.actions.comment_link_handler(event)
                return True
            elif handler_name == 'comment_text_handler':
                await self.actions.comment_text_handler(event)
                return True

        return False

class StatsHandler:
    def __init__(self, tbot):
        self.tbot = tbot

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

            text = "📊 Bot Statistics\n\n"
            for key, value in stats.items():
                text += f"• {key}: {value}\n"

            await event.respond(text)

        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await event.respond("Error showing statistics")

    async def show_groups(self, event):
        """Show all groups for all clients"""
        logger.info("show_groups in StatsHandler")
        try:
            clients_data = self.tbot.config.get('clients', {})
            
            if not isinstance(clients_data, dict) or not clients_data:
                await event.respond("No groups found. Please run 'Update Groups' first.")
                return
            
            text = "📋 Groups per Account:\n\n"
            total_groups = 0
            
            for session, groups in clients_data.items():
                phone = session.replace('.session', '') if session else 'Unknown'
                groups_count = len(groups) if isinstance(groups, list) else 0
                total_groups += groups_count
                text += f"• {phone}: {groups_count} groups\n"
            
            text += f"\n📊 Total: {total_groups} groups"
            await event.respond(text)

        except Exception as e:
            logger.error(f"Error showing groups: {e}")
            await event.respond("Error showing groups")

    async def show_keywords(self, event):
        """Show all configured keywords"""
        logger.info("show_keywords in StatsHandler")
        try:
            keywords = self.tbot.config.get('KEYWORDS', [])
            
            if not keywords:
                await event.respond("No keywords configured yet.")
                return
            
            text = "🔑 Configured Keywords:\n\n"
            for idx, keyword in enumerate(keywords, 1):
                text += f"{idx}. {keyword}\n"
            
            await event.respond(text)

        except Exception as e:
            logger.error(f"Error showing keywords: {e}")
            await event.respond("Error showing keywords")

    async def show_ignores(self, event):
        """Show all ignored users"""
        logger.info("show_ignores in StatsHandler")
        try:
            ignored_users = self.tbot.config.get('IGNORE_USERS', [])
            
            if not ignored_users:
                await event.respond("No users are currently ignored.")
                return
            
            text = "🚫 Ignored Users:\n\n"
            for idx, user_id in enumerate(ignored_users, 1):
                text += f"{idx}. User ID: `{user_id}`\n"
            
            await event.respond(text)

        except Exception as e:
            logger.error(f"Error showing ignored users: {e}")
            await event.respond("Error showing ignored users")


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
            'update_groups': self.account_handler.update_groups,
            'add_keyword': self.keyword_handler.add_keyword_handler,
            'remove_keyword': self.keyword_handler.remove_keyword_handler,
            'ignore_user': self.keyword_handler.ignore_user_handler,
            'remove_ignore_user': self.keyword_handler.delete_ignore_user_handler,
            'show_stats': self.stats_handler.show_stats,
            'show_groups': self.stats_handler.show_groups,
            'Show_keyword': self.stats_handler.show_keywords,
            'show_ignores': self.stats_handler.show_ignores,
            'monitor_mode': self.show_monitor_keyboard,
            'account_management': self.show_account_management_keyboard,
            'bulk_operations': self.show_bulk_operations_keyboard,
            'individual_keyboard': self.show_individual_keyboard,
            'report': self.show_report_keyboard,
            'exit': self.show_start_keyboard,
            # Bulk operations
            'bulk_reaction': self.handle_bulk_reaction,
            'bulk_poll': self.handle_bulk_poll,
            'bulk_join': self.handle_bulk_join,
            'bulk_block': self.handle_bulk_block,
            'bulk_send_pv': self.handle_bulk_send_pv,
            'bulk_comment': self.handle_bulk_comment,
            # Individual operations
            'send_pv': self.handle_individual_send_pv,
            'join': self.handle_individual_join,
            'left': self.handle_individual_left,
            'comment': self.handle_individual_comment,
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

    # Bulk operation handlers
    async def handle_bulk_reaction(self, event):
        """Handle bulk reaction operation"""
        logger.info("handle_bulk_reaction in CallbackHandler")
        await self.actions.prompt_group_action(event, 'reaction')

    async def handle_bulk_poll(self, event):
        """Handle bulk poll operation"""
        logger.info("handle_bulk_poll in CallbackHandler")
        await self.actions.prompt_group_action(event, 'poll')

    async def handle_bulk_join(self, event):
        """Handle bulk join operation"""
        logger.info("handle_bulk_join in CallbackHandler")
        await self.actions.prompt_group_action(event, 'join')

    async def handle_bulk_block(self, event):
        """Handle bulk block operation"""
        logger.info("handle_bulk_block in CallbackHandler")
        await self.actions.prompt_group_action(event, 'block')

    async def handle_bulk_send_pv(self, event):
        """Handle bulk send_pv operation"""
        logger.info("handle_bulk_send_pv in CallbackHandler")
        await self.actions.prompt_group_action(event, 'send_pv')

    async def handle_bulk_comment(self, event):
        """Handle bulk comment operation"""
        logger.info("handle_bulk_comment in CallbackHandler")
        await self.actions.prompt_group_action(event, 'comment')

    # Individual operation handlers
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

    async def handle_individual_comment(self, event):
        """Handle individual comment operation"""
        logger.info("handle_individual_comment in CallbackHandler")
        await self.actions.prompt_individual_action(event, 'comment')

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
                await self.tbot.client_manager.delete_session(session)
            # Handle reaction button selections
            elif data.startswith('reaction_') and data != 'reaction_link_handler':
                # Check if it's a reaction emoji selection (not a number)
                if data in ['reaction_thumbsup', 'reaction_heart', 'reaction_laugh', 'reaction_wow', 'reaction_sad', 'reaction_angry']:
                    await self.actions.reaction_select_handler(event)
                    return
            # Handle bulk action callbacks (e.g., "reaction_3" means 3 accounts for reaction)
            elif '_' in data:
                parts = data.split('_')
                if len(parts) == 2:
                    action_name, value = parts
                    # Check if it's a bulk operation with number of accounts
                    if value.isdigit() and action_name in ['reaction', 'poll', 'join', 'block', 'send_pv', 'comment']:
                        num_accounts = int(value)
                        await self.actions.handle_group_action(event, action_name, num_accounts)
                    # Check if it's an individual operation with session name
                    elif action_name in ['send_pv', 'join', 'left', 'comment']:
                        session = value
                        if session in self.tbot.active_clients:
                            account = self.tbot.active_clients[session]
                            await getattr(self.actions, action_name)(account, event)
                        else:
                            await event.respond(f"Account {session} not found.")
                    else:
                        # Try standard actions
                        action = self.callback_actions.get(data)
                        if action:
                            logger.info(f"{data} in callback_handler")
                            await action(event)
                        else:
                            logger.error(f"No handler found for callback data: {data}")
                            await event.respond("Unknown command.")
                else:
                    # Try standard actions
                    action = self.callback_actions.get(data)
                    if action:
                        logger.info(f"{data} in callback_handler")
                        await action(event)
                    else:
                        logger.error(f"No handler found for callback data: {data}")
                        await event.respond("Unknown command.")
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
