"""
Utility functions for common operations across the bot.
This module contains reusable functions to reduce code duplication.
"""
import logging
import asyncio
import random
from typing import Optional, Tuple, Callable, List, Any
from telethon.errors import FloodWaitError, SessionRevokedError
try:
    from telethon.errors.rpcerrorlist import AuthKeyUnregisteredError
except ImportError:
    AuthKeyUnregisteredError = None
from telethon import TelegramClient

logger = logging.getLogger(__name__)


def get_session_name(account: TelegramClient) -> str:
    """
    Extract session name from a TelegramClient instance.
    
    Args:
        account: TelegramClient instance
        
    Returns:
        Session name or 'Unknown' if extraction fails
    """
    try:
        if hasattr(account, 'session') and hasattr(account.session, 'filename'):
            return account.session.filename
    except (AttributeError, Exception):
        pass
    return 'Unknown'


async def cleanup_conversation_state(tbot, chat_id: int):
    """
    Clean up conversation state for a chat.
    
    Args:
        tbot: TelegramBot instance
        chat_id: Chat ID to clean up
    """
    async with tbot._conversations_lock:
        tbot._conversations.pop(chat_id, None)


def is_session_revoked_error(error: Exception) -> bool:
    """
    Check if an error indicates a revoked session.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error indicates revoked session
    """
    error_msg = str(error).lower()
    error_type = type(error).__name__.lower()
    # Check for AuthKeyUnregisteredError
    if AuthKeyUnregisteredError and isinstance(error, AuthKeyUnregisteredError):
        return True
    # Check error message and type
    return any(keyword in error_msg for keyword in ['session', 'revoked', 'not logged in', 'auth', 'invalid', 'key is not registered', 'unregistered']) or \
           any(keyword in error_type for keyword in ['revoked', 'auth', 'unregistered'])


async def check_admin_access(event, admin_id: int) -> bool:
    """
    Check if event sender is admin.
    
    Args:
        event: Telegram event
        admin_id: Admin user ID
        
    Returns:
        True if sender is admin or admin_id is 0 (for tests)
    """
    if admin_id == 0:
        return True  # Skip check in tests
    return event.sender_id == admin_id


async def execute_bulk_operation(
    accounts: List[TelegramClient],
    operation: Callable,
    operation_name: str,
    semaphore: asyncio.Semaphore,
    counter_lock: asyncio.Lock,
    delay_range: Tuple[float, float] = (2.0, 5.0)
) -> Tuple[int, int, List[str]]:
    """
    Execute a bulk operation across multiple accounts with proper error handling.
    
    Args:
        accounts: List of TelegramClient instances
        operation: Async function to execute for each account
        operation_name: Name of operation for logging
        semaphore: Semaphore for concurrency control
        counter_lock: Lock for thread-safe counter updates
        delay_range: Tuple of (min, max) delay between operations
        
    Returns:
        Tuple of (success_count, error_count, revoked_sessions)
    """
    success_count = 0
    error_count = 0
    revoked_sessions = []
    
    async def execute_with_account(acc):
        nonlocal success_count, error_count
        session_name = get_session_name(acc)
        
        async with semaphore:
            try:
                await operation(acc)
                async with counter_lock:
                    success_count += 1
                await asyncio.sleep(random.uniform(*delay_range))
            except FloodWaitError as e:
                async with counter_lock:
                    error_count += 1
                logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except (SessionRevokedError, ValueError) as e:
                if is_session_revoked_error(e):
                    async with counter_lock:
                        error_count += 1
                        revoked_sessions.append(session_name)
                    logger.warning(f"Session revoked for account {session_name}: {e}")
                else:
                    async with counter_lock:
                        error_count += 1
                    logger.error(f"Error in {operation_name} with account {session_name}: {e}")
            except Exception as e:
                async with counter_lock:
                    error_count += 1
                logger.error(f"Error in {operation_name} with account {session_name}: {e}")
    
    tasks = [execute_with_account(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return success_count, error_count, revoked_sessions


async def format_bulk_result_message(
    operation_name: str,
    success_count: int,
    error_count: int,
    revoked_sessions: List[str],
    success_emoji: str = "",
    error_emoji: str = ""
) -> str:
    """
    Format a result message for bulk operations.
    
    Args:
        operation_name: Name of the operation
        success_count: Number of successful operations
        error_count: Number of failed operations
        revoked_sessions: List of revoked session names
        success_emoji: Emoji for success message (deprecated, kept for compatibility)
        error_emoji: Emoji for error message (deprecated, kept for compatibility)
        
    Returns:
        Formatted message string
    """
    if error_count == 0:
        return f"{operation_name} completed successfully with {success_count} account(s)."
    else:
        msg = f"{operation_name} completed with {success_count} account(s). {error_count} account(s) encountered errors."
        if revoked_sessions:
            msg += f"\n{len(revoked_sessions)} account(s) were revoked and removed."
        return msg


def cleanup_handlers(tbot, handler_keys: List[str], chat_id: Optional[int] = None):
    """
    Clean up handler keys from tbot.handlers dictionary.
    
    Args:
        tbot: TelegramBot instance
        handler_keys: List of keys to remove from handlers
        chat_id: Optional chat_id to also clean conversation state
    """
    for key in handler_keys:
        tbot.handlers.pop(key, None)
    
    if chat_id is not None:
        asyncio.create_task(cleanup_conversation_state(tbot, chat_id))


def get_bot_user_id(bot_token: str) -> Optional[int]:
    """
    Extract bot user ID from bot token.
    
    Args:
        bot_token: Bot token string (format: "bot_id:bot_secret")
        
    Returns:
        Bot user ID or None if extraction fails
    """
    try:
        return int(bot_token.split(':')[0])
    except (ValueError, AttributeError, IndexError):
        return None


def is_bot_message(event, bot_token: str) -> bool:
    """
    Check if event is from the bot itself.
    
    Args:
        event: Telegram event
        bot_token: Bot token string
        
    Returns:
        True if message is from bot itself
    """
    bot_user_id = get_bot_user_id(bot_token)
    if bot_user_id is None:
        return False
    return event.sender_id == bot_user_id


async def cleanup_handlers_and_state(
    tbot,
    handler_keys: List[str],
    chat_id: Optional[int] = None
):
    """
    Clean up handler keys and conversation state.
    
    Args:
        tbot: TelegramBot instance
        handler_keys: List of keys to remove from handlers
        chat_id: Optional chat_id to also clean conversation state
    """
    for key in handler_keys:
        tbot.handlers.pop(key, None)
    
    if chat_id is not None:
        await cleanup_conversation_state(tbot, chat_id)


async def resolve_entity(peer, account):
    """
    Resolve entity from peer (can be str, int, or already resolved entity).
    
    Args:
        peer: Entity identifier (str username, int ID, or entity object)
        account: TelegramClient instance
        
    Returns:
        Resolved entity
        
    Raises:
        Exception: If entity cannot be resolved (e.g., revoked session)
    """
    if isinstance(peer, str):
        try:
            return await account.get_entity(peer)
        except Exception as e:
            # Check if it's a revoked session error
            if is_session_revoked_error(e) or (AuthKeyUnregisteredError and isinstance(e, AuthKeyUnregisteredError)):
                logger.error(f"Session revoked or unregistered while resolving entity: {e}")
                raise SessionRevokedError("Session revoked or unregistered")
            raise
    elif isinstance(peer, int) and peer < 0:
        try:
            return await account.get_entity(peer)
        except Exception as e:
            # Check if it's a revoked session error
            if is_session_revoked_error(e) or (AuthKeyUnregisteredError and isinstance(e, AuthKeyUnregisteredError)):
                logger.error(f"Session revoked or unregistered while resolving entity: {e}")
                raise SessionRevokedError("Session revoked or unregistered")
            raise
    return peer


async def send_error_message(tbot, chat_id: int, error: Exception, error_type: str = "general"):
    """
    Send appropriate error message based on error type.
    
    Args:
        tbot: TelegramBot instance
        chat_id: Chat ID to send message to
        error: Exception that occurred
        error_type: Type of error ('code', 'password', 'phone', 'general')
    """
    error_str = str(error).lower()
    
    error_messages = {
        'code': {
            'phone code invalid': "Invalid verification code.\n\nPlease start over with /start and try again.",
            'code invalid': "Invalid verification code.\n\nPlease start over with /start and try again.",
            'phone code expired': "Verification code has expired.\n\nPlease start over with /start and enter the code faster.",
            'code expired': "Verification code has expired.\n\nPlease start over with /start and enter the code faster.",
            'timeout': "Connection timeout.\n\nPlease check your internet and try again.",
            'default': f"Error verifying code: {str(error)[:100]}\n\nPlease start over with /start."
        },
        'password': {
            'password': "Invalid password.\n\nPlease start over with /start and try again with the correct password.",
            'timeout': "Connection timeout.\n\nPlease check your internet and try again.",
            'default': f"Error verifying password: {str(error)[:100]}\n\nPlease start over with /start."
        },
        'phone': {
            'flood': "Too many requests. Please wait a few minutes and try again.",
            'phone': "Invalid phone number. Please check the format and try again.",
            'network': "Network error. Please check your connection and try again.",
            'connection': "Network error. Please check your connection and try again.",
            'api': "API credentials error. Please contact the administrator.",
            'default': f"Failed to add account: {str(error)[:100]}..."
        },
        'general': {
            'default': f"Error: {str(error)[:100]}"
        }
    }
    
    messages = error_messages.get(error_type, error_messages['general'])
    
    # Find matching error message
    message = messages.get('default', "An error occurred. Please try again.")
    for key, msg in messages.items():
        if key != 'default' and key in error_str:
            message = msg
            break
    
    await tbot.tbot.send_message(chat_id, message)


def extract_account_name(client) -> str:
    """
    Extract account name from TelegramClient instance.
    
    Args:
        client: TelegramClient instance
        
    Returns:
        Account name or 'Unknown Account'
    """
    try:
        if hasattr(client, 'session') and hasattr(client.session, 'filename'):
            account_name = str(client.session.filename)
            # Remove .session extension if present
            if account_name.endswith('.session'):
                account_name = account_name[:-8]
            return account_name
    except Exception:
        pass
    return 'Unknown Account'


async def prompt_for_input(
    tbot,
    event,
    prompt_message: str,
    conversation_state: str,
    cancel_button: bool = True
):
    """
    Prompt user for input and set conversation state.
    
    Args:
        tbot: TelegramBot instance
        event: Telegram event
        prompt_message: Message to prompt user
        conversation_state: State name to set in conversations
        cancel_button: Whether to show cancel button
    """
    from telethon import Button
    buttons = [Button.inline("Cancel", 'cancel')] if cancel_button else None
    await event.respond(prompt_message, buttons=buttons)
    async with tbot._conversations_lock:
        tbot._conversations[event.chat_id] = conversation_state


async def validate_and_respond(
    event,
    validation_func,
    input_value: str,
    error_prefix: str = ""
) -> tuple[bool, any]:
    """
    Validate input and respond with error if invalid.
    
    Args:
        event: Telegram event
        validation_func: Validation function that returns (is_valid, error_msg, ...)
        input_value: Input value to validate
        error_prefix: Prefix for error messages
        
    Returns:
        Tuple of (is_valid, validated_value or None)
    """
    result = validation_func(input_value)
    is_valid = result[0]
    
    if not is_valid:
        error_msg = result[1] if len(result) > 1 else "Invalid input"
        await event.respond(f"{error_prefix} {error_msg}")
        return False, None
    
    # Return validated value if available
    validated_value = result[2] if len(result) > 2 else input_value
    return True, validated_value


async def check_account_exists(
    tbot,
    event,
    account_key: str = 'account',
    error_message: str = "Account not found. Please start over."
) -> tuple[bool, any]:
    """
    Check if account exists in handlers and respond with error if not.
    
    Args:
        tbot: TelegramBot instance
        event: Telegram event
        account_key: Key in handlers to check
        error_message: Error message to send if account not found
        
    Returns:
        Tuple of (exists, account or None)
    """
    account = tbot.handlers.get(account_key)
    if not account:
        await event.respond(error_message)
        await cleanup_conversation_state(tbot, event.chat_id)
        return False, None
    return True, account


async def remove_revoked_session_completely(tbot, session_name: str):
    """
    Completely remove a revoked session from active_clients, config, and delete session file.
    
    This is a centralized function to ensure revoked sessions are fully removed
    from all parts of the system.
    
    Args:
        tbot: TelegramBot instance
        session_name: Session name/key to remove
    """
    import os
    
    # Remove from active_clients
    async with tbot.active_clients_lock:
        if session_name in tbot.active_clients:
            client = tbot.active_clients[session_name]
            # Cleanup handlers before disconnecting
            if hasattr(tbot, 'monitor'):
                tbot.monitor.cleanup_client_handlers(client)
            try:
                await client.disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting client {session_name}: {e}")
            del tbot.active_clients[session_name]
            logger.info(f"Removed revoked session from active_clients: {session_name}")
    
    # Remove from config['clients']
    if session_name in tbot.config.get('clients', {}):
        del tbot.config['clients'][session_name]
        tbot.config_manager.save_config(tbot.config)
        logger.info(f"Removed revoked session from config: {session_name}")
    
    # Remove from inactive_accounts if present
    if 'inactive_accounts' in tbot.config and session_name in tbot.config['inactive_accounts']:
        del tbot.config['inactive_accounts'][session_name]
        tbot.config_manager.save_config(tbot.config)
        logger.info(f"Removed revoked session from inactive_accounts: {session_name}")
    
    # Delete session file
    session_file = f"{session_name}.session"
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
            logger.info(f"Deleted revoked session file: {session_file}")
        except OSError as e:
            logger.warning(f"Could not delete session file {session_file}: {e}")
    
    logger.info(f"Revoked session {session_name} completely removed from system")


async def check_accounts_available(
    tbot,
    event,
    accounts: list,
    error_message: str = "No active accounts found."
) -> bool:
    """
    Check if accounts list is not empty and respond with error if empty.
    
    Args:
        tbot: TelegramBot instance
        event: Telegram event
        accounts: List of accounts to check
        error_message: Error message to send if no accounts
        
    Returns:
        True if accounts available, False otherwise
    """
    if not accounts:
        await event.respond(error_message)
        await cleanup_conversation_state(tbot, event.chat_id)
        return False
    return True

