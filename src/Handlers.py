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

# Setting up the logger
logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.INFO)
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
                await self.tbot.client_manager.delete_session(session)
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
