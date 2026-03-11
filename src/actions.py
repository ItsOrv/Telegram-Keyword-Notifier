from __future__ import annotations

import logging
import random
import asyncio
from typing import List, Tuple, Callable, Optional
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import SendVoteRequest, SendReactionRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, SessionRevokedError
try:
    from telethon.tl.types import ReactionEmoji
except ImportError:
    # Fallback for older Telethon versions
    from telethon.tl import types
    ReactionEmoji = getattr(types, 'ReactionEmoji', None)
from src.Config import CHANNEL_ID, REPORT_CHECK_BOT
from src.Validation import InputValidator
from src.utils import (
    get_session_name, cleanup_conversation_state, is_session_revoked_error,
    execute_bulk_operation, format_bulk_result_message,
    cleanup_handlers_and_state, resolve_entity, prompt_for_input,
    check_account_exists, check_accounts_available,
    remove_revoked_session_completely
)
from src.constants import (
    MAX_CONCURRENT_OPERATIONS, MAX_RETRY_ATTEMPTS,
    DEFAULT_DELAY_MIN, DEFAULT_DELAY_MAX,
    MIN_POLL_OPTION, MAX_POLL_OPTION,
    REPORT_CHECK_DELAY, HandlerKeys, ConversationStates
)
from src.Keyboards import Keyboard

logger = logging.getLogger(__name__)

# Import constants from constants module
# MAX_CONCURRENT_OPERATIONS and MAX_RETRY_ATTEMPTS are now in constants.py

class Actions:
    """
    Handles all bulk and individual operations for Telegram accounts.
    
    This class provides methods for performing actions such as reactions, polls,
    joins, blocks, sending private messages, and comments using one or multiple
    Telegram accounts. It includes proper error handling, rate limiting, and
    thread-safe operations.
    """
    
    def __init__(self, tbot):
        """
        Initialize the Actions class.
        
        Args:
            tbot: TelegramBot instance containing configuration and client management
        """
        self.tbot = tbot
        self.operation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)
        self._counter_lock = asyncio.Lock()
    
    # ==================== Helper Methods ====================
    
    @staticmethod
    async def _check_connection(client):
        """
        Check if client is connected, handling both sync and async is_connected().
        
        Args:
            client: TelegramClient instance
            
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            is_conn = client.is_connected()
            # Handle both sync and async is_connected() for compatibility
            if asyncio.iscoroutine(is_conn):
                is_conn = await is_conn
            return bool(is_conn)
        except Exception:
            return False
    
    async def _handle_session_revoked_error(
        self, 
        event, 
        account, 
        operation_name: str,
        cleanup_keys: List[str],
        chat_id: int
    ) -> None:
        """
        Handle session revoked errors consistently across all operations.
        
        Args:
            event: Telegram event
            account: TelegramClient instance
            operation_name: Name of the operation for logging
            cleanup_keys: List of handler keys to clean up
            chat_id: Chat ID for cleanup
        """
        logger.error(f"Session revoked during {operation_name}")
        await event.respond("Your account has been revoked. Please add the account again.")
        session_name = get_session_name(account)
        if session_name:
            await remove_revoked_session_completely(self.tbot, session_name)
        await cleanup_handlers_and_state(self.tbot, cleanup_keys, chat_id)
    
    async def _handle_operation_error(
        self,
        event,
        error: Exception,
        operation_name: str,
        account=None,
        cleanup_keys: List[str] = None,
        chat_id: int = None
    ) -> None:
        """
        Handle operation errors consistently.
        
        Args:
            event: Telegram event
            error: Exception that occurred
            operation_name: Name of the operation
            account: Optional TelegramClient instance
            cleanup_keys: Optional list of handler keys to clean up
            chat_id: Optional chat ID for cleanup
        """
        if is_session_revoked_error(error):
            if account:
                await self._handle_session_revoked_error(
                    event, account, operation_name,
                    cleanup_keys or [], chat_id or event.chat_id
                )
            return
        
        logger.error(f"Error in {operation_name}: {error}")
        await event.respond(f"Error in {operation_name}: {str(error)}")
        
        if cleanup_keys and chat_id:
            await cleanup_handlers_and_state(self.tbot, cleanup_keys, chat_id)
    
    async def _validate_and_get_accounts(
        self,
        num_accounts: int,
        event=None
    ) -> Tuple[List[TelegramClient], bool]:
        """
        Validate and get connected accounts for bulk operations.
        
        Args:
            num_accounts: Number of accounts to get
            event: Optional Telegram event for error responses
            
        Returns:
            Tuple of (valid_accounts, success)
        """
        async with self.tbot.active_clients_lock:
            accounts = list(self.tbot.active_clients.values())[:num_accounts]
        
        if not accounts:
            if event:
                await event.respond("No active accounts found.")
            return [], False
        
        # Validate accounts are connected
        valid_accounts = []
        for acc in accounts:
            try:
                if await self._check_connection(acc):
                    valid_accounts.append(acc)
                else:
                    logger.warning(f"Account {get_session_name(acc)} is not connected, skipping")
            except Exception as e:
                logger.warning(f"Error checking connection for account {get_session_name(acc)}: {e}")
        
        if not valid_accounts:
            if event:
                await event.respond("No connected accounts available for this operation.")
            return [], False
        
        return valid_accounts, True
    
    async def _cleanup_operation_state(
        self,
        handler_keys: List[str],
        chat_id: int
    ) -> None:
        """
        Clean up operation state consistently.
        
        Args:
            handler_keys: List of handler keys to remove
            chat_id: Chat ID to clean conversation state
        """
        await cleanup_handlers_and_state(self.tbot, handler_keys, chat_id)
    
    def _get_handler_value(self, key: str, default=None):
        """Get handler value safely."""
        return self.tbot.handlers.get(key, default)
    
    def _set_handler_value(self, key: str, value):
        """Set handler value safely."""
        self.tbot.handlers[key] = value
    
    def _pop_handler_value(self, key: str, default=None):
        """Pop handler value safely."""
        return self.tbot.handlers.pop(key, default)
    
    async def _set_conversation_state(self, chat_id: int, state: str):
        """Set conversation state safely."""
        async with self.tbot._conversations_lock:
            self.tbot._conversations[chat_id] = state
    
    async def _clear_conversation_state(self, chat_id: int):
        """Clear conversation state safely."""
        async with self.tbot._conversations_lock:
            self.tbot._conversations.pop(chat_id, None)
    
    async def _execute_bulk_operation_with_validation(
        self,
        event,
        num_accounts: int,
        operation_func: Callable,
        operation_name: str,
        cleanup_keys: List[str]
    ) -> None:
        """
        Execute bulk operation with account validation and result reporting.
        
        Args:
            event: Telegram event
            num_accounts: Number of accounts to use
            operation_func: Async function that takes (account) and performs operation
            operation_name: Name of operation for reporting
            cleanup_keys: List of handler keys to clean up
        """
        valid_accounts, success = await self._validate_and_get_accounts(num_accounts, event)
        if not success:
            await self._clear_conversation_state(event.chat_id)
            return
        
        success_count, error_count, revoked_sessions = await self._execute_bulk_operation(
            valid_accounts, operation_func, operation_name
        )
        
        if revoked_sessions:
            await self._remove_revoked_sessions(revoked_sessions)
        
        result_message = await format_bulk_result_message(
            operation_name, success_count, error_count, revoked_sessions
        )
        await event.respond(result_message)
        
        await self._cleanup_operation_state(cleanup_keys, event.chat_id)
    
    async def _execute_bulk_operation(
        self,
        accounts: List[TelegramClient],
        operation_func: Callable,
        operation_name: str
    ) -> Tuple[int, int, List[str]]:
        """
        Execute a bulk operation across multiple accounts with proper error handling.
        
        Args:
            accounts: List of TelegramClient instances
            operation_func: Async function that takes (account) and performs the operation
            operation_name: Name of operation for logging
            
        Returns:
            Tuple of (success_count, error_count, revoked_sessions)
        """
        success_count = 0
        error_count = 0
        revoked_sessions = []
        
        async def execute_with_account(acc):
            nonlocal success_count, error_count, revoked_sessions
            session_name = get_session_name(acc)
            
            async with self.operation_semaphore:
                try:
                    await operation_func(acc)
                    async with self._counter_lock:
                        success_count += 1
                    await asyncio.sleep(random.uniform(DEFAULT_DELAY_MIN, DEFAULT_DELAY_MAX))
                except FloodWaitError as e:
                    async with self._counter_lock:
                        error_count += 1
                    logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                except (SessionRevokedError, ValueError) as e:
                    if is_session_revoked_error(e):
                        async with self._counter_lock:
                            error_count += 1
                            revoked_sessions.append(session_name)
                        logger.warning(f"Session revoked for account {session_name}: {e}")
                    else:
                        async with self._counter_lock:
                            error_count += 1
                        logger.error(f"Error in {operation_name} with account {session_name}: {e}")
                except Exception as e:
                    async with self._counter_lock:
                        error_count += 1
                    logger.error(f"Error in {operation_name} with account {session_name}: {e}")
        
        tasks = [execute_with_account(acc) for acc in accounts]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return success_count, error_count, revoked_sessions
    
    async def _execute_with_retry(self, operation, account, max_retries=None, operation_name="operation"):
        """
        Execute an operation with automatic retry logic for transient errors.
        
        Args:
            operation: Async callable to execute
            account: TelegramClient instance
            max_retries: Maximum number of retry attempts
            operation_name: Name of operation for logging
            
        Returns:
            Tuple of (success: bool, error: Exception or None)
        """
        if max_retries is None:
            max_retries = MAX_RETRY_ATTEMPTS
        
        session_name = get_session_name(account)
        
        last_error = None
        for attempt in range(max_retries):
            try:
                await operation()
                return True, None
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"FloodWaitError for account {session_name} (attempt {attempt + 1}/{max_retries}): waiting {wait_time} seconds")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return False, e
            except (SessionRevokedError, ValueError) as e:
                error_msg = str(e).lower()
                if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                    logger.warning(f"Session revoked for account {session_name}: {e}")
                    return False, e
                # For other ValueError, retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    last_error = e
                    continue
                return False, e
            except Exception as e:
                error_msg = str(e).lower()
                # Retry on network/connection errors
                if any(keyword in error_msg for keyword in ['network', 'connection', 'timeout', 'temporary']):
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Network error for account {session_name} (attempt {attempt + 1}/{max_retries}): retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        last_error = e
                        continue
                # Don't retry on other errors
                return False, e
        
        return False, last_error

    def _clean_telegram_link(self, link: str) -> str:
        """
        Clean Telegram link by removing protocol, query params, and fragments.
        
        Args:
            link: Raw Telegram link
            
        Returns:
            Cleaned link string
        """
        clean_link = link.replace('https://', '').replace('http://', '').strip()
        if '?' in clean_link:
            clean_link = clean_link.split('?')[0]
        if '#' in clean_link:
            clean_link = clean_link.split('#')[0]
        return clean_link
    
    def _parse_private_channel_link(self, clean_link: str) -> Optional[Tuple[int, int]]:
        """
        Parse private channel/group link format: t.me/c/123456/789
        
        Args:
            clean_link: Cleaned link string
            
        Returns:
            Tuple of (chat_id, message_id) or None if parsing fails
        """
        if '/c/' not in clean_link:
            return None
        
        parts = clean_link.split('/c/')
        if len(parts) != 2:
            return None
        
        chat_and_msg = parts[1].split('/')
        if len(chat_and_msg) < 2:
            return None
        
        try:
            chat_id_str = chat_and_msg[0].strip()
            message_id_str = chat_and_msg[1].strip()
            
            if not chat_id_str.isdigit() or not message_id_str.isdigit():
                logger.error(f"Invalid chat_id or message_id format in private link")
                return None
            
            chat_id = int('-100' + chat_id_str)
            message_id = int(message_id_str)
            
            if message_id <= 0:
                logger.error(f"Invalid message_id (must be positive): {message_id}")
                return None
            
            return chat_id, message_id
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing private channel link: {e}")
            return None
    
    async def _parse_public_channel_link(
        self,
        clean_link: str,
        account: Optional[TelegramClient] = None
    ) -> Optional[Tuple[any, int]]:
        """
        Parse public channel/group link format: t.me/username/123
        
        Args:
            clean_link: Cleaned link string
            account: Optional TelegramClient to resolve username
            
        Returns:
            Tuple of (entity/username, message_id) or None if parsing fails
        """
        if 't.me/' not in clean_link:
            return None
        
        parts = clean_link.split('t.me/')
        if len(parts) != 2:
            return None
        
        rest = parts[1].split('/')
        if len(rest) < 2:
            return None
        
        try:
            chat_username = rest[0].strip()
            message_id_str = rest[1].strip()
            
            if not message_id_str.isdigit():
                logger.error(f"Invalid message_id format in public link")
                return None
            
            message_id = int(message_id_str)
            
            if message_id <= 0:
                logger.error(f"Invalid message_id (must be positive): {message_id}")
                return None
            
            # Try to resolve username if account is provided
            if account:
                try:
                    entity = await account.get_entity(chat_username)
                    return entity, message_id
                except Exception as e:
                    logger.warning(f"Error resolving username {chat_username}: {e}. Will try to resolve later.")
                    return chat_username, message_id
            
            return chat_username, message_id
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing public channel link: {e}")
            return None
    
    async def parse_telegram_link(self, link: str, account=None):
        """
        Parse a Telegram link to extract chat_id/entity and message_id.
        Resolves username to entity if account is provided.
        
        Args:
            link: Telegram message link (e.g., https://t.me/c/123456/789 or https://t.me/username/123)
            account: Optional TelegramClient instance to resolve usernames
            
        Returns:
            Tuple of (chat_id/entity, message_id) or (None, None) if parsing fails
        """
        try:
            clean_link = self._clean_telegram_link(link)
            
            # Try parsing as private channel first
            result = self._parse_private_channel_link(clean_link)
            if result is not None:
                return result
            
            # Try parsing as public channel
            result = await self._parse_public_channel_link(clean_link, account)
            if result is not None:
                return result
            
            logger.error(f"Unable to parse link format: {link}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error parsing Telegram link {link}: {e}", exc_info=True)
            return None, None

    async def _remove_revoked_sessions(self, revoked_sessions):
        """
        Remove revoked sessions from active_clients, config, and delete session files.
        
        Args:
            revoked_sessions: List of session names/filenames to remove
        """
        async with self.tbot.active_clients_lock:
            for session_name in revoked_sessions:
                # Find the actual key in active_clients
                removed_key = None
                for key, client in list(self.tbot.active_clients.items()):
                    try:
                        client_session_name = get_session_name(client)
                        if client_session_name == session_name or key == session_name:
                            removed_key = key
                            break
                    except (AttributeError, KeyError, Exception) as e:
                        logger.debug(f"Error checking session for {key}: {e}")
                        pass
                
                # Use the key we found or the session_name directly
                session_key = removed_key if removed_key else session_name
                
                # Use the centralized removal function
                await remove_revoked_session_completely(self.tbot, session_key)

    async def prompt_group_action(self, event, action_name):
        """
        Prompt the user to enter the number of accounts to be used for the group action.
        """
        async with self.tbot.active_clients_lock:
            total_accounts = len(self.tbot.active_clients)
        
        message = f"There are {total_accounts} accounts available.\n\nPlease choose how many accounts (from 1 to {total_accounts}) will perform the {action_name} action:"
        # Organize buttons in rows of 3 for better layout
        buttons = []
        for i in range(1, total_accounts + 1, 3):
            row = [Button.inline(str(i), f"{action_name}_{i}")]
            if i + 1 <= total_accounts:
                row.append(Button.inline(str(i + 1), f"{action_name}_{i + 1}"))
            if i + 2 <= total_accounts:
                row.append(Button.inline(str(i + 2), f"{action_name}_{i + 2}"))
            buttons.append(row)
        # Add cancel button
        buttons = Keyboard.add_cancel_button(buttons)
        await event.respond(message, buttons=buttons)

    async def prompt_individual_action(self, event, action_name: str) -> None:
        """
        Prompt user to select an account for individual operation.
        
        Args:
            event: Telegram event (CallbackQuery or NewMessage)
            action_name: Name of the action (e.g., 'reaction', 'send_pv')
        """
        async with self.tbot.active_clients_lock:
            sessions = list(self.tbot.active_clients.keys())
        
        if not sessions:
            await event.respond("No accounts available for this operation.")
            return
        
        # Organize buttons in rows of 2 for better layout
        buttons = []
        for i in range(0, len(sessions), 2):
            row = [Button.inline(sessions[i], f"{action_name}_{sessions[i]}")]
            if i + 1 < len(sessions):
                row.append(Button.inline(sessions[i + 1], f"{action_name}_{sessions[i + 1]}"))
            buttons.append(row)
        
        # Add cancel button
        buttons = Keyboard.add_cancel_button(buttons)
        await event.respond("Please select an account to perform the action:", buttons=buttons)

    async def handle_group_action(self, event, action_name, num_accounts):
        """
        Handle the group action by calling the respective bulk function.
        For bulk operations, we use dedicated bulk handlers that ask for input once.
        """
        # Map action names to bulk handler functions
        bulk_handlers = {
            'reaction': self.bulk_reaction,
            'poll': self.bulk_poll,
            'join': self.bulk_join,
            'leave': self.bulk_leave,
            'block': self.bulk_block,
            'send_pv': self.bulk_send_pv,
            'comment': self.bulk_comment
        }
        
        bulk_handler = bulk_handlers.get(action_name)
        if bulk_handler:
            await bulk_handler(event, num_accounts)
        else:
            await event.respond(f"Bulk operation for {action_name} is not supported.")

    async def handle_individual_action(self, event, action_name: str, session: str) -> None:
        """
        Handle individual action for a specific account.
        
        Args:
            event: Telegram event
            action_name: Name of the action to perform
            session: Session name of the account to use
        """
        async with self.tbot.active_clients_lock:
            account = self.tbot.active_clients.get(session)
        
        if account:
            await getattr(self, action_name)(account, event)
        else:
            await event.respond(f"Account {session} not found.")

    async def bulk_reaction(self, event, num_accounts):
        """
        Handle bulk reaction operation - ask for link and reaction once, then apply with all accounts.
        """
        try:
            self._set_handler_value(HandlerKeys.REACTION_NUM_ACCOUNTS, num_accounts)
            self._set_handler_value(HandlerKeys.REACTION_IS_BULK, True)
            await event.respond("Please send the message link to apply reaction:")
            await self._set_conversation_state(event.chat_id, ConversationStates.REACTION_LINK_HANDLER)
        except Exception as e:
            logger.error(f"Error in bulk_reaction: {e}")
            await event.respond("Error starting bulk reaction operation.")
            self._pop_handler_value(HandlerKeys.REACTION_NUM_ACCOUNTS)
            self._pop_handler_value(HandlerKeys.REACTION_IS_BULK)

    async def reaction(self, account, event):
        """
        Perform the reaction action for individual operations.
        """
        # Step 1: Ask for the link to the message
        await prompt_for_input(
            self.tbot, event,
            "Please send the message link to apply reaction:",
            ConversationStates.REACTION_LINK_HANDLER
        )
        self._set_handler_value(HandlerKeys.REACTION_ACCOUNT, account)
        self._set_handler_value(HandlerKeys.REACTION_IS_BULK, False)

    async def reaction_link_handler(self, event):
        """
        Handle the link input for the reaction action (both bulk and individual).
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            self._set_handler_value(HandlerKeys.REACTION_LINK, link)
            reaction_buttons = [
                [
                    Button.inline("Thumbs Up", 'reaction_thumbsup'),
                    Button.inline("Heart", 'reaction_heart'),
                    Button.inline("Laugh", 'reaction_laugh')
                ],
                [
                    Button.inline("Wow", 'reaction_wow'),
                    Button.inline("Sad", 'reaction_sad'),
                    Button.inline("Angry", 'reaction_angry')
                ]
            ]
            # Add cancel button
            reaction_buttons = Keyboard.add_cancel_button(reaction_buttons)
            await event.respond("Please select a reaction:", buttons=reaction_buttons)
        except Exception as e:
            logger.error(f"Error in reaction_link_handler: {e}")
            await event.respond("Error processing link. Please try again.")
            cleanup_keys = [
                HandlerKeys.REACTION_LINK,
                HandlerKeys.REACTION_NUM_ACCOUNTS,
                HandlerKeys.REACTION_IS_BULK,
                HandlerKeys.REACTION_ACCOUNT
            ]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)

    async def _get_reaction_from_data(self, data: str) -> str:
        """
        Get reaction emoji from callback data.
        
        Args:
            data: Callback data string
            
        Returns:
            Reaction emoji or None if invalid
        """
        reaction_map = {
            'reaction_thumbsup': '👍',
            'reaction_heart': '❤️',
            'reaction_laugh': '😂',
            'reaction_wow': '😮',
            'reaction_sad': '😢',
            'reaction_angry': '😡'
        }
        return reaction_map.get(data)
    
    async def _execute_bulk_reaction(
        self,
        event,
        link: str,
        reaction: str,
        num_accounts: int
    ) -> None:
        """
        Execute bulk reaction operation.
        
        Args:
            event: Telegram event
            link: Message link
            reaction: Reaction emoji
            num_accounts: Number of accounts to use
        """
        valid_accounts, success = await self._validate_and_get_accounts(num_accounts, event)
        if not success:
            await self._clear_conversation_state(event.chat_id)
            return
        
        async def reaction_operation(acc):
            if not await self._check_connection(acc):
                raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
            await self.apply_reaction(acc, link, reaction)
        
        success_count, error_count, revoked_sessions = await self._execute_bulk_operation(
            valid_accounts, reaction_operation, 'reaction'
        )
        
        if revoked_sessions:
            await self._remove_revoked_sessions(revoked_sessions)
        
        result_message = await format_bulk_result_message(
            f'reaction {reaction}', success_count, error_count, revoked_sessions
        )
        await event.respond(result_message)
        
        cleanup_keys = [
            HandlerKeys.REACTION_LINK,
            HandlerKeys.REACTION,
            HandlerKeys.REACTION_NUM_ACCOUNTS,
            HandlerKeys.REACTION_IS_BULK
        ]
        await self._cleanup_operation_state(cleanup_keys, event.chat_id)
    
    async def _execute_individual_reaction(
        self,
        event,
        account,
        link: str,
        reaction: str
    ) -> None:
        """
        Execute individual reaction operation.
        
        Args:
            event: Telegram event
            account: TelegramClient instance
            link: Message link
            reaction: Reaction emoji
        """
        try:
            await self.apply_reaction(account, link, reaction)
            account_name = get_session_name(account)
            await event.respond(f"Reaction {reaction} applied successfully with account {account_name}.")
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'reaction', account,
                [
                    HandlerKeys.REACTION_LINK,
                    HandlerKeys.REACTION,
                    HandlerKeys.REACTION_ACCOUNT,
                    HandlerKeys.REACTION_IS_BULK
                ],
                event.chat_id
            )
            return
        
        cleanup_keys = [
            HandlerKeys.REACTION_LINK,
            HandlerKeys.REACTION,
            HandlerKeys.REACTION_ACCOUNT,
            HandlerKeys.REACTION_IS_BULK
        ]
        await self._cleanup_operation_state(cleanup_keys, event.chat_id)
    
    async def reaction_select_handler(self, event) -> None:
        """
        Handle reaction selection for both bulk and individual operations.
        
        Processes the selected reaction emoji and applies it to the target message
        using the appropriate account(s) based on the operation type.
        
        Args:
            event: Telegram CallbackQuery event containing reaction selection
        """
        data = event.data.decode() if hasattr(event, 'data') else ''
        reaction = await self._get_reaction_from_data(data)
        
        if reaction is None:
            logger.warning(f"Invalid reaction selected: {data}")
            await event.respond("Invalid reaction selected. Please try again.")
            await self._clear_conversation_state(event.chat_id)
            return
        
        self._set_handler_value(HandlerKeys.REACTION, reaction)
        
        is_bulk = self._get_handler_value(HandlerKeys.REACTION_IS_BULK, False)
        link = self._get_handler_value(HandlerKeys.REACTION_LINK)
        
        if not link:
            await event.respond("Link not found. Please start over.")
            await self._clear_conversation_state(event.chat_id)
            return
        
        if is_bulk:
            num_accounts = self._get_handler_value(HandlerKeys.REACTION_NUM_ACCOUNTS)
            if num_accounts is None:
                await event.respond("Number of accounts not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            await self._execute_bulk_reaction(event, link, reaction, num_accounts)
        else:
            account = self._get_handler_value(HandlerKeys.REACTION_ACCOUNT)
            if account:
                await self._execute_individual_reaction(event, account, link, reaction)
            else:
                await event.respond("Account not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)


    async def apply_reaction(self, account, link, reaction):
        """
        Apply the selected reaction using the given account.
        
        Args:
            account: TelegramClient instance
            link: Telegram message link
            reaction: Reaction emoji string
        """
        try:
            # Parse the link to get chat_id/entity and message_id
            chat_entity, message_id = await self.parse_telegram_link(link, account)
            
            if chat_entity is None or message_id is None:
                raise ValueError(f"Failed to parse link: {link}")
            
            # If chat_entity is a string (username), resolve it
            try:
                chat_entity = await resolve_entity(chat_entity, account)
            except SessionRevokedError:
                logger.error(f"Session revoked while applying reaction")
                raise
            except Exception as e:
                if is_session_revoked_error(e):
                    logger.error(f"Session revoked while resolving entity for reaction: {e}")
                    raise SessionRevokedError("Session revoked or unregistered")
                raise
            
            # Create reaction emoji object
            # Try different methods based on Telethon version
            if ReactionEmoji:
                reaction_emoji = ReactionEmoji(emoticon=reaction)
                reaction_obj = [reaction_emoji]
            else:
                # Fallback: use string directly (for older Telethon versions)
                reaction_obj = [reaction]
            
            # Send reaction using SendReactionRequest
            await account(SendReactionRequest(
                peer=chat_entity,
                msg_id=message_id,
                reaction=reaction_obj
            ))
            
            logger.info(f"Applied {reaction} reaction to message {message_id} using account {get_session_name(account)}")
        except SessionRevokedError:
            logger.error(f"Session revoked while applying reaction")
            raise
        except Exception as e:
            if is_session_revoked_error(e):
                logger.error(f"Session revoked while applying reaction: {e}")
                raise SessionRevokedError("Session revoked or unregistered")
            logger.error(f"Error applying reaction: {e}", exc_info=True)
            raise  # Re-raise to allow caller to handle

    async def poll(self, account, event) -> None:
        """
        Initiate poll voting operation for individual account.
        
        Prompts user for poll link and option selection.
        
        Args:
            account: TelegramClient instance to use
            event: Telegram event
        """
        await prompt_for_input(
            self.tbot, event,
            "Please send the poll link:",
            ConversationStates.POLL_LINK_HANDLER
        )
        self._set_handler_value(HandlerKeys.POLL_ACCOUNT, account)
        self._set_handler_value(HandlerKeys.POLL_IS_BULK, False)

    async def poll_link_handler(self, event):
        """
        Handle the poll link input for both bulk and individual operations.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            self._set_handler_value(HandlerKeys.POLL_LINK, link)
            await event.respond("Please enter the option number (e.g., 1, 2, 3):")
            await self._set_conversation_state(event.chat_id, ConversationStates.POLL_OPTION_HANDLER)
        except Exception as e:
            logger.error(f"Error in poll_link_handler: {e}")
            await event.respond("Error processing link. Please try again.")
            cleanup_keys = [
                HandlerKeys.POLL_ACCOUNT,
                HandlerKeys.POLL_LINK,
                HandlerKeys.POLL_NUM_ACCOUNTS,
                HandlerKeys.POLL_IS_BULK
            ]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)

    async def _validate_poll_and_option(
        self,
        account: TelegramClient,
        link: str,
        option: int
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validate that link points to a poll and option is valid.
        
        Args:
            account: TelegramClient instance
            link: Poll link
            option: Option index (0-based)
            
        Returns:
            Tuple of (is_valid, error_message, poll_options_count)
        """
        try:
            chat_entity, message_id = await self.parse_telegram_link(link, account)
            if chat_entity is None or message_id is None:
                return False, "Error parsing link", None
            
            chat_entity = await resolve_entity(chat_entity, account)
            message = await account.get_messages(chat_entity, ids=message_id)
            
            if not message.poll:
                return False, "The provided link does not point to a poll.", None
            
            poll_options_count = len(message.poll.poll.answers) if message.poll and message.poll.poll else 0
            if option >= poll_options_count:
                return False, f"Invalid option number. Poll has {poll_options_count} options.", poll_options_count
            
            return True, None, poll_options_count
        except Exception as e:
            logger.error(f"Error validating poll: {e}")
            return False, f"Error verifying poll: {str(e)}", None
    
    async def _execute_bulk_poll_vote(
        self,
        event,
        link: str,
        option: int,
        option_num: int,
        num_accounts: int
    ) -> None:
        """
        Execute bulk poll vote operation.
        
        Args:
            event: Telegram event
            link: Poll link
            option: Option index (0-based)
            option_num: Option number (1-based, for display)
            num_accounts: Number of accounts to use
        """
        valid_accounts, success = await self._validate_and_get_accounts(num_accounts, event)
        if not success:
            await self._clear_conversation_state(event.chat_id)
            return
        
        # Validate poll using first account
        is_valid, error_msg, _ = await self._validate_poll_and_option(valid_accounts[0], link, option)
        if not is_valid:
            await event.respond(error_msg)
            cleanup_keys = [HandlerKeys.POLL_LINK, HandlerKeys.POLL_NUM_ACCOUNTS, HandlerKeys.POLL_IS_BULK]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)
            return
        
        # Parse link once
        chat_entity, message_id = await self.parse_telegram_link(link, valid_accounts[0])
        
        async def vote_operation(acc):
            if not await self._check_connection(acc):
                raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
            peer = await resolve_entity(chat_entity, acc)
            message = await acc.get_messages(peer, ids=message_id)
            if not message.poll:
                raise ValueError("Link does not point to a poll")
            await acc(SendVoteRequest(peer=peer, msg_id=message_id, options=[bytes([option])]))
        
        success_count, error_count, revoked_sessions = await self._execute_bulk_operation(
            valid_accounts, vote_operation, 'vote'
        )
        
        if revoked_sessions:
            await self._remove_revoked_sessions(revoked_sessions)
        
        result_message = await format_bulk_result_message(
            f'Vote for option {option_num}', success_count, error_count, revoked_sessions
        )
        await event.respond(result_message)
        
        cleanup_keys = [HandlerKeys.POLL_LINK, HandlerKeys.POLL_NUM_ACCOUNTS, HandlerKeys.POLL_IS_BULK]
        await self._cleanup_operation_state(cleanup_keys, event.chat_id)
    
    async def _execute_individual_poll_vote(
        self,
        event,
        account: TelegramClient,
        link: str,
        option: int,
        option_num: int
    ) -> None:
        """
        Execute individual poll vote operation.
        
        Args:
            event: Telegram event
            account: TelegramClient instance
            link: Poll link
            option: Option index (0-based)
            option_num: Option number (1-based, for display)
        """
        chat_entity, message_id = await self.parse_telegram_link(link, account)
        if chat_entity is None or message_id is None:
            raise ValueError(f"Failed to parse poll link: {link}")
        
        try:
            chat_entity = await resolve_entity(chat_entity, account)
            message = await account.get_messages(chat_entity, ids=message_id)
            
            if message.poll:
                await account(SendVoteRequest(
                    peer=chat_entity,
                    msg_id=message_id,
                    options=[bytes([option])]
                ))
                account_name = get_session_name(account)
                await event.respond(f"Voted for option {option_num} successfully with account {account_name}.")
            else:
                await event.respond("The provided link does not point to a poll.")
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'poll vote', account,
                [HandlerKeys.POLL_ACCOUNT, HandlerKeys.POLL_LINK],
                event.chat_id
            )
            return
        
        cleanup_keys = [HandlerKeys.POLL_ACCOUNT, HandlerKeys.POLL_LINK]
        await self._cleanup_operation_state(cleanup_keys, event.chat_id)

    async def poll_option_handler(self, event):
        """
        Handle the poll option selection for both bulk and individual operations.
        """
        try:
            # Validate poll option
            is_valid, error_msg, option_num = InputValidator.validate_poll_option(event.message.text.strip())
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            option = option_num - 1  # Convert to 0-based index
            link = self._get_handler_value(HandlerKeys.POLL_LINK)
            is_bulk = self._get_handler_value(HandlerKeys.POLL_IS_BULK, False)
            
            if is_bulk:
                num_accounts = self._get_handler_value(HandlerKeys.POLL_NUM_ACCOUNTS)
                if num_accounts is None:
                    await event.respond("Number of accounts not found. Please start over.")
                    await self._clear_conversation_state(event.chat_id)
                    return
                await self._execute_bulk_poll_vote(event, link, option, option_num, num_accounts)
            else:
                account = self._get_handler_value(HandlerKeys.POLL_ACCOUNT)
                if not account:
                    await event.respond("Account not found. Please start over.")
                    await self._clear_conversation_state(event.chat_id)
                    return
                await self._execute_individual_poll_vote(event, account, link, option, option_num)
            
        except Exception as e:
            logger.error(f"Error voting on poll: {e}")
            await event.respond(f"Error voting on poll: {str(e)}")
            cleanup_keys = [
                HandlerKeys.POLL_ACCOUNT,
                HandlerKeys.POLL_LINK,
                HandlerKeys.POLL_NUM_ACCOUNTS,
                HandlerKeys.POLL_IS_BULK
            ]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)


    async def join(self, account, event):
        """
        Perform the join action - join a group or channel.
        """
        await prompt_for_input(
            self.tbot, event,
            "Please send the group/channel link or username to join:",
            ConversationStates.JOIN_LINK_HANDLER
        )
        self._set_handler_value(HandlerKeys.JOIN_ACCOUNT, account)

    async def join_link_handler(self, event):
        """
        Handle the join link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}")
                return
            
            account = self._get_handler_value(HandlerKeys.JOIN_ACCOUNT)
            if not account:
                await event.respond("Account not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            # Join the group/channel
            # Try join_chat first (newer telethon), fallback to JoinChannelRequest
            try:
                if hasattr(account, 'join_chat'):
                    await account.join_chat(link)
                else:
                    entity = await resolve_entity(link, account)
                    await account(JoinChannelRequest(entity))
            except AttributeError:
                entity = await resolve_entity(link, account)
                await account(JoinChannelRequest(entity))
            except Exception as e:
                if is_session_revoked_error(e):
                    await self._handle_session_revoked_error(
                        event, account, 'join',
                        [HandlerKeys.JOIN_ACCOUNT], event.chat_id
                    )
                raise
            account_name = get_session_name(account)
            await event.respond(f"Successfully joined {link} with account {account_name}.")
            
            # Cleanup
            await self._cleanup_operation_state([HandlerKeys.JOIN_ACCOUNT], event.chat_id)
            
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'join', account,
                [HandlerKeys.JOIN_ACCOUNT], event.chat_id
            )

    async def left(self, account, event):
        """
        Perform the left action - leave a group or channel.
        """
        await prompt_for_input(
            self.tbot, event,
            "Please send the group/channel link or username to leave:",
            ConversationStates.LEFT_LINK_HANDLER
        )
        self._set_handler_value(HandlerKeys.LEFT_ACCOUNT, account)

    async def left_link_handler(self, event):
        """
        Handle the leave link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}")
                return
            
            account = self._get_handler_value(HandlerKeys.LEFT_ACCOUNT)
            if not account:
                await event.respond("Account not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            # Leave the group/channel
            try:
                entity = await account.get_entity(link)
                await account.leave_chat(entity)
                account_name = get_session_name(account)
                await event.respond(f"Successfully left {link} with account {account_name}.")
            except Exception as e:
                if is_session_revoked_error(e):
                    await self._handle_session_revoked_error(
                        event, account, 'leave',
                        [HandlerKeys.LEFT_ACCOUNT], event.chat_id
                    )
                    return
                raise
            
            # Cleanup
            await self._cleanup_operation_state([HandlerKeys.LEFT_ACCOUNT], event.chat_id)
            
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'leave', account,
                [HandlerKeys.LEFT_ACCOUNT], event.chat_id
            )

    async def block(self, account, event):
        """
        Perform the block action - block a user.
        """
        await prompt_for_input(
            self.tbot, event,
            "Please send the user ID or username to block:",
            ConversationStates.BLOCK_USER_HANDLER
        )
        self._set_handler_value(HandlerKeys.BLOCK_ACCOUNT, account)

    async def block_user_handler(self, event):
        """
        Handle the block user input.
        """
        try:
            user_input = event.message.text.strip()
            account = self._get_handler_value(HandlerKeys.BLOCK_ACCOUNT)
            if not account:
                await event.respond("Account not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            # Block the user
            from telethon.tl.functions.contacts import BlockRequest
            try:
                entity = await resolve_entity(user_input, account)
                await account(BlockRequest(entity))
                account_name = get_session_name(account)
                await event.respond(f"User {user_input} blocked successfully with account {account_name}.")
            except Exception as e:
                if is_session_revoked_error(e):
                    await self._handle_session_revoked_error(
                        event, account, 'block',
                        [HandlerKeys.BLOCK_ACCOUNT], event.chat_id
                    )
                    return
                raise
            
            # Cleanup
            await self._cleanup_operation_state([HandlerKeys.BLOCK_ACCOUNT], event.chat_id)
            
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'block', account,
                [HandlerKeys.BLOCK_ACCOUNT], event.chat_id
            )

    async def send_pv(self, account, event):
        """
        Perform the send_pv action - send a private message to a user.
        """
        await prompt_for_input(
            self.tbot, event,
            "Please send the user ID or username to send message:",
            ConversationStates.SEND_PV_USER_HANDLER
        )
        self._set_handler_value(HandlerKeys.SEND_PV_ACCOUNT, account)

    async def send_pv_user_handler(self, event):
        """
        Handle the send_pv user input.
        """
        try:
            user_input = event.message.text.strip()
            self._set_handler_value(HandlerKeys.SEND_PV_USER, user_input)
            await event.respond("Please send the message text:")
            await self._set_conversation_state(event.chat_id, ConversationStates.SEND_PV_MESSAGE_HANDLER)
        except Exception as e:
            logger.error(f"Error in send_pv_user_handler: {e}")
            await event.respond("Error processing user information. Please try again.")
            cleanup_keys = [HandlerKeys.SEND_PV_ACCOUNT, HandlerKeys.SEND_PV_USER]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)

    async def send_pv_message_handler(self, event):
        """
        Handle the send_pv message input.
        """
        try:
            message = event.message.text.strip()
            
            # Validate message text
            is_valid, error_msg = InputValidator.validate_message_text(message)
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            account = self._get_handler_value(HandlerKeys.SEND_PV_ACCOUNT)
            user_input = self._get_handler_value(HandlerKeys.SEND_PV_USER)
            if not account:
                await event.respond("Account not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            # Send the private message
            try:
                entity = await resolve_entity(user_input, account)
                await account.send_message(entity, message)
                account_name = get_session_name(account)
                await event.respond(f"Message sent successfully to {user_input} with account {account_name}.")
            except Exception as e:
                if is_session_revoked_error(e):
                    await self._handle_session_revoked_error(
                        event, account, 'send_pv',
                        [HandlerKeys.SEND_PV_ACCOUNT, HandlerKeys.SEND_PV_USER], event.chat_id
                    )
                    return
                raise
            
            # Cleanup
            cleanup_keys = [HandlerKeys.SEND_PV_ACCOUNT, HandlerKeys.SEND_PV_USER]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)
            
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'send_pv', account,
                [HandlerKeys.SEND_PV_ACCOUNT, HandlerKeys.SEND_PV_USER], event.chat_id
            )

    async def comment(self, account, event) -> None:
        """
        Initiate comment operation for individual account.
        
        Prompts user for post/message link to comment on.
        
        Args:
            account: TelegramClient instance to use
            event: Telegram event
        """
        await prompt_for_input(
            self.tbot, event,
            "Please send the post/message link to comment:",
            ConversationStates.COMMENT_LINK_HANDLER
        )
        self._set_handler_value(HandlerKeys.COMMENT_ACCOUNT, account)

    async def comment_link_handler(self, event):
        """
        Handle the comment link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            self._set_handler_value(HandlerKeys.COMMENT_LINK, link)
            await event.respond("Please enter your comment:")
            await self._set_conversation_state(event.chat_id, ConversationStates.COMMENT_TEXT_HANDLER)
        except Exception as e:
            logger.error(f"Error in comment_link_handler: {e}")
            await event.respond("Error processing link. Please try again.")
            cleanup_keys = [HandlerKeys.COMMENT_ACCOUNT, HandlerKeys.COMMENT_LINK]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)

    async def comment_text_handler(self, event):
        """
        Handle the comment text input.
        """
        try:
            comment_text = event.message.text.strip()
            
            # Validate comment text
            is_valid, error_msg = InputValidator.validate_message_text(comment_text)
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            account = self._get_handler_value(HandlerKeys.COMMENT_ACCOUNT)
            link = self._get_handler_value(HandlerKeys.COMMENT_LINK)
            is_bulk = self._get_handler_value(HandlerKeys.COMMENT_IS_BULK, False)
            
            if is_bulk:
                # This is a bulk operation
                num_accounts = self._get_handler_value(HandlerKeys.COMMENT_NUM_ACCOUNTS)
                if num_accounts is None:
                    await event.respond("Number of accounts not found. Please start over.")
                    await self._clear_conversation_state(event.chat_id)
                    return
                
                valid_accounts, success = await self._validate_and_get_accounts(num_accounts, event)
                if not success:
                    await self._clear_conversation_state(event.chat_id)
                    return
                
                # Parse link once using first valid account
                chat_entity, message_id = await self.parse_telegram_link(link, valid_accounts[0] if valid_accounts else None)
                
                if chat_entity is None or message_id is None:
                    await event.respond(f"Error parsing link: {link}")
                    cleanup_keys = [
                        HandlerKeys.COMMENT_LINK,
                        HandlerKeys.COMMENT_NUM_ACCOUNTS,
                        HandlerKeys.COMMENT_IS_BULK
                    ]
                    await self._cleanup_operation_state(cleanup_keys, event.chat_id)
                    return
                
                # Comment with all valid accounts
                async def comment_operation(acc):
                    if not await self._check_connection(acc):
                        raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
                    peer = await resolve_entity(chat_entity, acc)
                    await acc.send_message(peer, comment_text, reply_to=message_id)
                
                success_count, error_count, revoked_sessions = await self._execute_bulk_operation(
                    valid_accounts, comment_operation, 'comment'
                )
                
                if revoked_sessions:
                    await self._remove_revoked_sessions(revoked_sessions)
                
                result_message = await format_bulk_result_message(
                    'Comment', success_count, error_count, revoked_sessions
                )
                await event.respond(result_message)
                
                cleanup_keys = [
                    HandlerKeys.COMMENT_LINK,
                    HandlerKeys.COMMENT_NUM_ACCOUNTS,
                    HandlerKeys.COMMENT_IS_BULK
                ]
                await self._cleanup_operation_state(cleanup_keys, event.chat_id)
            else:
                # Individual operation
                if not account:
                    await event.respond("Account not found. Please start over.")
                    await self._clear_conversation_state(event.chat_id)
                    return
                
                chat_entity, message_id = await self.parse_telegram_link(link, account)
                
                if chat_entity is None or message_id is None:
                    raise ValueError(f"Failed to parse comment link: {link}")
                
                # Resolve entity if needed
                try:
                    chat_entity = await resolve_entity(chat_entity, account)
                    await account.send_message(chat_entity, comment_text, reply_to=message_id)
                    await event.respond(f"Comment sent successfully.")
                except Exception as e:
                    if is_session_revoked_error(e):
                        await self._handle_session_revoked_error(
                            event, account, 'comment',
                            [HandlerKeys.COMMENT_ACCOUNT, HandlerKeys.COMMENT_LINK], event.chat_id
                        )
                        return
                    raise
                
                cleanup_keys = [HandlerKeys.COMMENT_ACCOUNT, HandlerKeys.COMMENT_LINK]
                await self._cleanup_operation_state(cleanup_keys, event.chat_id)
            
        except Exception as e:
            await self._handle_operation_error(
                event, e, 'comment', account,
                [
                    HandlerKeys.COMMENT_ACCOUNT,
                    HandlerKeys.COMMENT_LINK,
                    HandlerKeys.COMMENT_NUM_ACCOUNTS,
                    HandlerKeys.COMMENT_IS_BULK
                ],
                event.chat_id
            )

    # ==================== Bulk Operation Handlers ====================
    
    async def bulk_poll(self, event, num_accounts):
        """
        Handle bulk poll operation - ask for link and option once, then vote with all accounts.
        """
        try:
            self._set_handler_value(HandlerKeys.POLL_NUM_ACCOUNTS, num_accounts)
            self._set_handler_value(HandlerKeys.POLL_IS_BULK, True)
            await event.respond("Please send the poll link:")
            await self._set_conversation_state(event.chat_id, ConversationStates.POLL_LINK_HANDLER)
        except Exception as e:
            logger.error(f"Error in bulk_poll: {e}")
            await event.respond("Error starting bulk poll operation.")
            self._pop_handler_value(HandlerKeys.POLL_NUM_ACCOUNTS)
            self._pop_handler_value(HandlerKeys.POLL_IS_BULK)
    
    async def bulk_join(self, event, num_accounts):
        """
        Handle bulk join operation - ask for link once, then join with all accounts.
        """
        try:
            await event.respond("Please send the group/channel link to join:")
            await self._set_conversation_state(event.chat_id, ConversationStates.BULK_JOIN_LINK_HANDLER)
            self._set_handler_value(HandlerKeys.JOIN_NUM_ACCOUNTS, num_accounts)
        except Exception as e:
            logger.error(f"Error in bulk_join: {e}")
            await event.respond("Error starting bulk join operation.")
            self.tbot.handlers.pop('join_num_accounts', None)
    
    async def bulk_join_link_handler(self, event):
        """
        Handle bulk join link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                self.tbot.handlers.pop('join_num_accounts', None)
                return
            
            num_accounts = self._get_handler_value(HandlerKeys.JOIN_NUM_ACCOUNTS)
            if num_accounts is None:
                await event.respond("Number of accounts not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            async def join_operation(acc):
                if not await self._check_connection(acc):
                    raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
                try:
                    if hasattr(acc, 'join_chat'):
                        await acc.join_chat(link)
                    else:
                        entity = await resolve_entity(link, acc)
                        await acc(JoinChannelRequest(entity))
                except AttributeError:
                    entity = await resolve_entity(link, acc)
                    await acc(JoinChannelRequest(entity))
            
            await self._execute_bulk_operation_with_validation(
                event, num_accounts, join_operation, 'Join',
                [HandlerKeys.JOIN_NUM_ACCOUNTS]
            )
            
        except Exception as e:
            logger.error(f"Error in bulk_join_link_handler: {e}")
            await event.respond(f"Error joining group/channel: {str(e)}")
            await self._cleanup_operation_state([HandlerKeys.JOIN_NUM_ACCOUNTS], event.chat_id)
    
    async def bulk_leave(self, event, num_accounts):
        """
        Handle bulk leave operation - ask for link once, then leave with all accounts.
        """
        try:
            await event.respond("Please send the group/channel link to leave:")
            await self._set_conversation_state(event.chat_id, ConversationStates.BULK_LEAVE_LINK_HANDLER)
            self._set_handler_value(HandlerKeys.LEAVE_NUM_ACCOUNTS, num_accounts)
        except Exception as e:
            logger.error(f"Error in bulk_leave: {e}")
            await event.respond("Error starting bulk leave operation.")
            self.tbot.handlers.pop('leave_num_accounts', None)
    
    async def bulk_leave_link_handler(self, event):
        """
        Handle bulk leave link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"{error_msg}")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                self.tbot.handlers.pop('leave_num_accounts', None)
                return
            
            num_accounts = self._get_handler_value(HandlerKeys.LEAVE_NUM_ACCOUNTS)
            if num_accounts is None:
                await event.respond("Number of accounts not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            async def leave_operation(acc):
                if not await self._check_connection(acc):
                    raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
                entity = await resolve_entity(link, acc)
                await acc.leave_chat(entity)
            
            await self._execute_bulk_operation_with_validation(
                event, num_accounts, leave_operation, 'Leave',
                [HandlerKeys.LEAVE_NUM_ACCOUNTS]
            )
            
        except Exception as e:
            logger.error(f"Error in bulk_leave_link_handler: {e}")
            await event.respond(f"Error leaving group/channel: {str(e)}")
            await self._cleanup_operation_state([HandlerKeys.LEAVE_NUM_ACCOUNTS], event.chat_id)
    
    async def bulk_block(self, event, num_accounts):
        """
        Handle bulk block operation - ask for user once, then block with all accounts.
        """
        try:
            await event.respond("Please send the user ID or username to block:")
            await self._set_conversation_state(event.chat_id, ConversationStates.BULK_BLOCK_USER_HANDLER)
            self._set_handler_value(HandlerKeys.BLOCK_NUM_ACCOUNTS, num_accounts)
        except Exception as e:
            logger.error(f"Error in bulk_block: {e}")
            await event.respond("Error starting bulk block operation.")
            self.tbot.handlers.pop('block_num_accounts', None)
    
    async def bulk_block_user_handler(self, event):
        """
        Handle bulk block user input.
        """
        try:
            user_input = event.message.text.strip()
            
            num_accounts = self._get_handler_value(HandlerKeys.BLOCK_NUM_ACCOUNTS)
            if num_accounts is None:
                await event.respond("Number of accounts not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            from telethon.tl.functions.contacts import BlockRequest
            async def block_operation(acc):
                if not await self._check_connection(acc):
                    raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
                entity = await resolve_entity(user_input, acc)
                await acc(BlockRequest(entity))
            
            await self._execute_bulk_operation_with_validation(
                event, num_accounts, block_operation, f'Block user {user_input}',
                [HandlerKeys.BLOCK_NUM_ACCOUNTS]
            )
            
        except Exception as e:
            logger.error(f"Error in bulk_block_user_handler: {e}")
            await event.respond(f"Error blocking user: {str(e)}")
            await self._cleanup_operation_state([HandlerKeys.BLOCK_NUM_ACCOUNTS], event.chat_id)
    
    async def bulk_send_pv_account_count_handler(self, event):
        """
        Handle bulk send_pv account count input.
        This handler is called when user provides the number of accounts to use.
        """
        try:
            user_input = event.message.text.strip()
            logger.info(f"User input for account count: '{user_input}'")

            # Get total available accounts
            async with self.tbot.active_clients_lock:
                total_accounts = len(self.tbot.active_clients)
            logger.info(f"Total available accounts: {total_accounts}")

            # Validate input is a number
            if not user_input.isdigit():
                logger.warning(f"Invalid input: '{user_input}' is not a digit")
                await event.respond(f"Please enter a valid number between 1 and {total_accounts}.")
                return

            num_accounts = int(user_input)
            logger.info(f"Parsed number: {num_accounts}")

            # Validate range
            if num_accounts < 1 or num_accounts > total_accounts:
                logger.warning(f"Number {num_accounts} is out of range 1-{total_accounts}")
                await event.respond(f"Please enter a number between 1 and {total_accounts}.")
                return

            # Store the number and proceed to ask for username
            logger.info("Proceeding to ask for username")
            self._set_handler_value(HandlerKeys.SEND_PV_NUM_ACCOUNTS, num_accounts)
            await event.respond("Please send the user ID or username to send message:")
            await self._set_conversation_state(event.chat_id, ConversationStates.BULK_SEND_PV_USER_HANDLER)
        except Exception as e:
            logger.error(f"Error in bulk_send_pv_account_count_handler: {e}")
            await event.respond("Error processing account count. Please try again.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def bulk_send_pv(self, event, num_accounts):
        """
        Handle bulk send_pv operation - ask for user and message once, then send with all accounts.
        """
        try:
            await event.respond("Please send the user ID or username to send message:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_send_pv_user_handler'
            self.tbot.handlers['send_pv_num_accounts'] = num_accounts
        except Exception as e:
            logger.error(f"Error in bulk_send_pv: {e}")
            await event.respond("Error starting bulk send_pv operation.")
            self.tbot.handlers.pop('send_pv_num_accounts', None)
    
    async def bulk_send_pv_user_handler(self, event) -> None:
        """
        Handle bulk send_pv user input and prompt for message text.
        
        Args:
            event: Telegram NewMessage event containing user ID/username
        """
        try:
            user_input = event.message.text.strip()
            self._set_handler_value(HandlerKeys.SEND_PV_USER, user_input)
            await event.respond("Please send the message text:")
            await self._set_conversation_state(event.chat_id, ConversationStates.BULK_SEND_PV_MESSAGE_HANDLER)
        except Exception as e:
            logger.error(f"Error in bulk_send_pv_user_handler: {e}")
            await event.respond("Error processing user information. Please try again.")
            cleanup_keys = [HandlerKeys.SEND_PV_NUM_ACCOUNTS, HandlerKeys.SEND_PV_USER]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)
    
    async def bulk_send_pv_message_handler(self, event):
        """
        Handle bulk send_pv message input.
        """
        try:
            message = event.message.text.strip()
            
            # Validate message text
            is_valid, error_msg = InputValidator.validate_message_text(message)
            if not is_valid:
                await event.respond(f"{error_msg}\nPlease try again.")
                return
            
            user_input = self._get_handler_value(HandlerKeys.SEND_PV_USER)
            num_accounts = self._get_handler_value(HandlerKeys.SEND_PV_NUM_ACCOUNTS)
            if num_accounts is None:
                await event.respond("Number of accounts not found. Please start over.")
                await self._clear_conversation_state(event.chat_id)
                return
            
            async def send_pv_operation(acc):
                if not await self._check_connection(acc):
                    raise ConnectionError(f"Account {get_session_name(acc)} is not connected")
                entity = await resolve_entity(user_input, acc)
                await acc.send_message(entity, message)
            
            await self._execute_bulk_operation_with_validation(
                event, num_accounts, send_pv_operation, 'Send message',
                [HandlerKeys.SEND_PV_NUM_ACCOUNTS, HandlerKeys.SEND_PV_USER]
            )
            
        except Exception as e:
            logger.error(f"Error in bulk_send_pv_message_handler: {e}")
            await event.respond(f"Error sending private message: {str(e)}")
            cleanup_keys = [HandlerKeys.SEND_PV_NUM_ACCOUNTS, HandlerKeys.SEND_PV_USER]
            await self._cleanup_operation_state(cleanup_keys, event.chat_id)
    
    async def bulk_comment(self, event, num_accounts):
        """
        Handle bulk comment operation - ask for link and text once, then comment with all accounts.
        """
        try:
            self._set_handler_value(HandlerKeys.COMMENT_NUM_ACCOUNTS, num_accounts)
            self._set_handler_value(HandlerKeys.COMMENT_IS_BULK, True)
            await event.respond("Please send the post/message link to comment:")
            await self._set_conversation_state(event.chat_id, ConversationStates.COMMENT_LINK_HANDLER)
        except Exception as e:
            logger.error(f"Error in bulk_comment: {e}")
            await event.respond("Error starting bulk comment operation.")
            self._pop_handler_value(HandlerKeys.COMMENT_NUM_ACCOUNTS)
            self._pop_handler_value(HandlerKeys.COMMENT_IS_BULK)
    
    async def check_report_status(self, phone_number: str, account) -> bool:
        """
        Check if an account has been reported by querying the report check bot.
        
        Args:
            phone_number: Phone number of the account to check
            account: TelegramClient instance for the account
            
        Returns:
            True if account is reported, False otherwise
        """
        if not REPORT_CHECK_BOT:
            logger.warning("REPORT_CHECK_BOT not configured, cannot check report status")
            return False
        
        try:
            # Send a message to the report check bot with the phone number
            try:
                report_bot = await account.get_entity(REPORT_CHECK_BOT)
                message = await account.send_message(report_bot, phone_number)
                
                # Wait a bit for the bot to respond
                await asyncio.sleep(REPORT_CHECK_DELAY)
                
                # Get the response from the bot
                async for response in account.iter_messages(report_bot, limit=1):
                    response_text = response.text.lower() if response.text else ""
                    
                    # Check if the response indicates the account is reported
                    # Common indicators: "reported", "banned", "restricted", etc.
                    reported_keywords = ['reported', 'banned', 'restricted', 'blocked', 'yes', 'true', '1']
                    is_reported = any(keyword in response_text for keyword in reported_keywords)
                    
                    # Clean up the messages
                    try:
                        await message.delete()
                        await response.delete()
                    except (Exception, AttributeError):
                        pass
                    
                    return is_reported
                
                # If no response, assume not reported
                try:
                    await message.delete()
                except (Exception, AttributeError):
                    pass
                return False
                
            except Exception as e:
                logger.error(f"Error checking report status for {phone_number}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in check_report_status for {phone_number}: {e}")
            return False

