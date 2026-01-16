import logging
import random
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import SendVoteRequest, SendReactionRequest
from telethon.errors import FloodWaitError, SessionRevokedError
try:
    from telethon.tl.types import ReactionEmoji
except ImportError:
    # Fallback for older Telethon versions
    from telethon.tl import types
    ReactionEmoji = getattr(types, 'ReactionEmoji', None)
from src.Config import CHANNEL_ID, REPORT_CHECK_BOT
from src.Validation import InputValidator

logger = logging.getLogger(__name__)

# Concurrency limit for bulk operations to avoid rate limiting
MAX_CONCURRENT_OPERATIONS = 3

# Maximum retry attempts for operations
MAX_RETRY_ATTEMPTS = 3

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
    
    async def _execute_with_retry(self, operation, account, max_retries=3, operation_name="operation"):
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
        session_name = None
        try:
            session_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
        except (AttributeError, Exception):
            session_name = 'Unknown'
        
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
            # Remove protocol if present
            clean_link = link.replace('https://', '').replace('http://', '').strip()
            
            # Handle t.me/c/123456/789 format (private channels/groups)
            if '/c/' in clean_link:
                parts = clean_link.split('/c/')
                if len(parts) == 2:
                    chat_and_msg = parts[1].split('/')
                    if len(chat_and_msg) >= 2:
                        try:
                            chat_id = int('-100' + chat_and_msg[0])
                            message_id = int(chat_and_msg[1])
                            return chat_id, message_id
                        except ValueError:
                            logger.error(f"Invalid chat_id or message_id in link: {link}")
                            return None, None
            
            # Handle t.me/username/123 format (public channels/groups)
            if 't.me/' in clean_link:
                parts = clean_link.split('t.me/')
                if len(parts) == 2:
                    rest = parts[1].split('/')
                    if len(rest) >= 2:
                        chat_username = rest[0]
                        try:
                            message_id = int(rest[1])
                            # If account is provided, resolve username to entity
                            if account:
                                try:
                                    entity = await account.get_entity(chat_username)
                                    return entity, message_id
                                except Exception as e:
                                    logger.error(f"Error resolving username {chat_username}: {e}")
                                    return None, None
                            else:
                                return chat_username, message_id
                        except ValueError:
                            logger.error(f"Invalid message_id in link: {link}")
                            return None, None
            
            logger.error(f"Unable to parse link format: {link}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error parsing Telegram link {link}: {e}", exc_info=True)
            return None, None

    async def _remove_revoked_sessions(self, revoked_sessions):
        """
        Remove revoked sessions from active_clients dictionary.
        
        Args:
            revoked_sessions: List of session names/filenames to remove
        """
        async with self.tbot.active_clients_lock:
            for session_name in revoked_sessions:
                # Find and remove the session
                for key, client in list(self.tbot.active_clients.items()):
                    try:
                        if hasattr(client, 'session') and hasattr(client.session, 'filename'):
                            if client.session.filename == session_name:
                                del self.tbot.active_clients[key]
                                logger.info(f"Removed revoked session: {key}")
                                break
                    except (AttributeError, KeyError, Exception) as e:
                        logger.debug(f"Error checking session for {key}: {e}")
                        pass

    async def prompt_group_action(self, event, action_name):
        """
        Prompt the user to enter the number of accounts to be used for the group action.
        """
        async with self.tbot.active_clients_lock:
            total_accounts = len(self.tbot.active_clients)
        
        message = f"There are {total_accounts} accounts available. Please choose how many accounts (from 1 to {total_accounts}) will perform the {action_name} action."
        buttons = [Button.inline(str(i), f"{action_name}_{i}") for i in range(1, total_accounts + 1)]
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
            await event.respond("❌ No accounts available for this operation.")
            return
        
        buttons = [Button.inline(session, f"{action_name}_{session}") for session in sessions]
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
            await event.respond(f"❌ عملیات bulk برای {action_name} پشتیبانی نمی‌شود.")

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
            self.tbot.handlers['reaction_num_accounts'] = num_accounts
            self.tbot.handlers['reaction_is_bulk'] = True
            await event.respond("لطفاً لینک پیام را برای اعمال reaction ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'reaction_link_handler'
        except Exception as e:
            logger.error(f"Error in bulk_reaction: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk reaction.")
            self.tbot.handlers.pop('reaction_num_accounts', None)
            self.tbot.handlers.pop('reaction_is_bulk', None)

    async def reaction(self, account, event):
        """
        Perform the reaction action for individual operations.
        """
        # Step 1: Ask for the link to the message
        await event.respond("لطفاً لینک پیام را برای اعمال reaction ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'reaction_link_handler'
        self.tbot.handlers['reaction_account'] = account
        self.tbot.handlers['reaction_is_bulk'] = False

    async def reaction_link_handler(self, event):
        """
        Handle the link input for the reaction action (both bulk and individual).
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            self.tbot.handlers['reaction_link'] = link
            await event.respond("لطفاً reaction مورد نظر را انتخاب کنید:", buttons=[
                Button.inline("👍", b'reaction_thumbsup'),
                Button.inline("❤️", b'reaction_heart'),
                Button.inline("😂", b'reaction_laugh'),
                Button.inline("😮", b'reaction_wow'),
                Button.inline("😢", b'reaction_sad'),
                Button.inline("😡", b'reaction_angry')
            ])
        except Exception as e:
            logger.error(f"Error in reaction_link_handler: {e}")
            await event.respond("❌ خطا در پردازش لینک. لطفاً دوباره تلاش کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('reaction_link', None)
            self.tbot.handlers.pop('reaction_num_accounts', None)
            self.tbot.handlers.pop('reaction_is_bulk', None)
            self.tbot.handlers.pop('reaction_account', None)

    async def reaction_select_handler(self, event) -> None:
        """
        Handle reaction selection for both bulk and individual operations.
        
        Processes the selected reaction emoji and applies it to the target message
        using the appropriate account(s) based on the operation type.
        
        Args:
            event: Telegram CallbackQuery event containing reaction selection
        """
        reaction_map = {
            'reaction_thumbsup': '👍',
            'reaction_heart': '❤️',
            'reaction_laugh': '😂',
            'reaction_wow': '😮',
            'reaction_sad': '😢',
            'reaction_angry': '😡'
        }
        
        data = event.data.decode() if hasattr(event, 'data') else ''
        reaction = reaction_map.get(data, data)
        self.tbot.handlers['reaction'] = reaction
        
        is_bulk = self.tbot.handlers.get('reaction_is_bulk', False)
        link = self.tbot.handlers.get('reaction_link')
        
        if not link:
            await event.respond("❌ لینک یافت نشد. لطفاً دوباره شروع کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            return
        
        if is_bulk:
            # Bulk operation - apply reaction with all selected accounts
            num_accounts = self.tbot.handlers.get('reaction_num_accounts')
            if num_accounts is None:
                await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            if not accounts:
                await event.respond("❌ هیچ حساب فعالی یافت نشد.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            success_count = 0
            error_count = 0
            revoked_sessions = []
            
            async def apply_reaction_with_limit(acc):
                nonlocal success_count, error_count
                session_name = None
                try:
                    session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                except (AttributeError, Exception):
                    session_name = 'Unknown'
                
                async with self.operation_semaphore:
                    try:
                        await self.apply_reaction(acc, link, reaction)
                        async with self._counter_lock:
                            success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except FloodWaitError as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (SessionRevokedError, ValueError) as e:
                        error_msg = str(e).lower()
                        if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                            async with self._counter_lock:
                                error_count += 1
                                revoked_sessions.append(session_name)
                            logger.warning(f"Session revoked for account {session_name}: {e}")
                        else:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error applying reaction with account {session_name}: {e}")
                    except Exception as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.error(f"Error applying reaction with account {session_name}: {e}")
            
            # Execute all reactions with concurrency control
            tasks = [apply_reaction_with_limit(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Remove revoked sessions from active_clients
            if revoked_sessions:
                await self._remove_revoked_sessions(revoked_sessions)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت reaction {reaction} با {success_count} حساب اعمال شد.")
            else:
                msg = f"⚠️ reaction {reaction} با {success_count} حساب اعمال شد. {error_count} حساب با خطا مواجه شد."
                if revoked_sessions:
                    msg += f"\n⚠️ {len(revoked_sessions)} حساب revoked شده و حذف شدند."
                await event.respond(msg)
            
            # Cleanup
            self.tbot.handlers.pop('reaction_link', None)
            self.tbot.handlers.pop('reaction', None)
            self.tbot.handlers.pop('reaction_num_accounts', None)
            self.tbot.handlers.pop('reaction_is_bulk', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
        else:
            # Individual operation
            account = self.tbot.handlers.get('reaction_account')
            if account:
                try:
                    await self.apply_reaction(account, link, reaction)
                    account_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
                    await event.respond(f"✅ با موفقیت reaction {reaction} با حساب {account_name} اعمال شد.")
                except Exception as e:
                    logger.error(f"Error applying reaction: {e}")
                    await event.respond(f"❌ خطا در اعمال reaction: {str(e)}")
                
                # Cleanup
                self.tbot.handlers.pop('reaction_link', None)
                self.tbot.handlers.pop('reaction', None)
                self.tbot.handlers.pop('reaction_account', None)
                self.tbot.handlers.pop('reaction_is_bulk', None)
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
            else:
                await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)


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
            if isinstance(chat_entity, str):
                chat_entity = await account.get_entity(chat_entity)
            
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
            
            logger.info(f"Applied {reaction} reaction to message {message_id} using account {account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'}")
        except Exception as e:
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
        await event.respond("لطفاً لینک نظرسنجی را ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'poll_link_handler'
        self.tbot.handlers['poll_account'] = account
        self.tbot.handlers['poll_is_bulk'] = False

    async def poll_link_handler(self, event):
        """
        Handle the poll link input for both bulk and individual operations.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            self.tbot.handlers['poll_link'] = link
            await event.respond("لطفاً شماره گزینه مورد نظر را وارد کنید (مثلاً 1، 2، 3):")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'poll_option_handler'
        except Exception as e:
            logger.error(f"Error in poll_link_handler: {e}")
            await event.respond("❌ خطا در پردازش لینک. لطفاً دوباره تلاش کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('poll_account', None)
            self.tbot.handlers.pop('poll_link', None)
            self.tbot.handlers.pop('poll_num_accounts', None)
            self.tbot.handlers.pop('poll_is_bulk', None)

    async def poll_option_handler(self, event):
        """
        Handle the poll option selection for both bulk and individual operations.
        """
        try:
            # Validate poll option
            is_valid, error_msg, option_num = InputValidator.validate_poll_option(event.message.text.strip())
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            option = option_num - 1  # Convert to 0-based index
            link = self.tbot.handlers.get('poll_link')
            is_bulk = self.tbot.handlers.get('poll_is_bulk', False)
            
            if is_bulk:
                # Bulk operation
                num_accounts = self.tbot.handlers.get('poll_num_accounts')
                if num_accounts is None:
                    await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    return
                
                async with self.tbot.active_clients_lock:
                    accounts = list(self.tbot.active_clients.values())[:num_accounts]
                
                if not accounts:
                    await event.respond("❌ هیچ حساب فعالی یافت نشد.")
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    return
                
                # Parse link once
                chat_entity, message_id = await self.parse_telegram_link(link, accounts[0] if accounts else None)
                
                if chat_entity is None or message_id is None:
                    await event.respond(f"❌ خطا در parse کردن لینک: {link}")
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    self.tbot.handlers.pop('poll_link', None)
                    self.tbot.handlers.pop('poll_num_accounts', None)
                    self.tbot.handlers.pop('poll_is_bulk', None)
                    return
                
                # Vote with all accounts
                success_count = 0
                error_count = 0
                revoked_sessions = []
                
                async def vote_with_account(acc):
                    nonlocal success_count, error_count
                    session_name = None
                    try:
                        session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                    except (AttributeError, Exception):
                        session_name = 'Unknown'
                    
                    async with self.operation_semaphore:
                        try:
                            # Resolve entity if needed
                            peer = chat_entity
                            if isinstance(peer, str):
                                peer = await acc.get_entity(peer)
                            elif isinstance(peer, int) and peer < 0:
                                peer = await acc.get_entity(peer)
                            
                            # Verify it's a poll
                            message = await acc.get_messages(peer, ids=message_id)
                            if not message.poll:
                                raise ValueError("Link does not point to a poll")
                            
                            await acc(SendVoteRequest(
                                peer=peer,
                                msg_id=message_id,
                                options=[bytes([option])]
                            ))
                            async with self._counter_lock:
                                success_count += 1
                            await asyncio.sleep(random.uniform(2, 5))
                        except FloodWaitError as e:
                            async with self._counter_lock:
                                error_count += 1
                            logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                            await asyncio.sleep(e.seconds)
                        except (SessionRevokedError, ValueError) as e:
                            error_msg = str(e).lower()
                            if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                                async with self._counter_lock:
                                    error_count += 1
                                    revoked_sessions.append(session_name)
                                logger.warning(f"Session revoked for account {session_name}: {e}")
                            else:
                                async with self._counter_lock:
                                    error_count += 1
                                logger.error(f"Error voting on poll with account {session_name}: {e}")
                        except Exception as e:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error voting on poll with account {session_name}: {e}")
                
                tasks = [vote_with_account(acc) for acc in accounts]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Report results
                if error_count == 0:
                    await event.respond(f"✅ با موفقیت به گزینه {option_num} با {success_count} حساب رای داده شد.")
                else:
                    await event.respond(f"⚠️ به گزینه {option_num} با {success_count} حساب رای داده شد. {error_count} حساب با خطا مواجه شد.")
                
                # Cleanup
                self.tbot.handlers.pop('poll_link', None)
                self.tbot.handlers.pop('poll_num_accounts', None)
                self.tbot.handlers.pop('poll_is_bulk', None)
            else:
                # Individual operation
                account = self.tbot.handlers.get('poll_account')
                if not account:
                    await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    return
                
                chat_entity, message_id = await self.parse_telegram_link(link, account)
                
                if chat_entity is None or message_id is None:
                    raise ValueError(f"Failed to parse poll link: {link}")
                
                # Resolve entity if needed
                if isinstance(chat_entity, str):
                    chat_entity = await account.get_entity(chat_entity)
                
                # Get the poll message
                message = await account.get_messages(chat_entity, ids=message_id)
                if message.poll:
                    await account(SendVoteRequest(
                        peer=chat_entity,
                        msg_id=message_id,
                        options=[bytes([option])]
                    ))
                    account_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
                    await event.respond(f"✅ با موفقیت به گزینه {option_num} با حساب {account_name} رای داده شد.")
                else:
                    await event.respond("❌ لینک ارائه شده به یک نظرسنجی اشاره نمی‌کند.")
            
            # Cleanup
            self.tbot.handlers.pop('poll_account', None)
            self.tbot.handlers.pop('poll_link', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error voting on poll: {e}")
            await event.respond(f"❌ خطا در رای دادن به نظرسنجی: {str(e)}")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            # Cleanup
            self.tbot.handlers.pop('poll_account', None)
            self.tbot.handlers.pop('poll_link', None)
            self.tbot.handlers.pop('poll_num_accounts', None)
            self.tbot.handlers.pop('poll_is_bulk', None)


    async def join(self, account, event):
        """
        Perform the join action - join a group or channel.
        """
        await event.respond("لطفاً لینک یا نام کاربری گروه/کانال را برای عضویت ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'join_link_handler'
        self.tbot.handlers['join_account'] = account

    async def join_link_handler(self, event):
        """
        Handle the join link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}")
                return
            
            account = self.tbot.handlers.get('join_account')
            if not account:
                await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            # Join the group/channel
            await account.join_chat(link)
            account_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
            await event.respond(f"✅ با موفقیت به {link} با حساب {account_name} عضو شدید.")
            
            # Cleanup
            self.tbot.handlers.pop('join_account', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error joining group/channel: {e}")
            await event.respond(f"❌ خطا در عضویت به گروه/کانال: {str(e)}")
            # Cleanup on error
            self.tbot.handlers.pop('join_account', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def left(self, account, event):
        """
        Perform the left action - leave a group or channel.
        """
        await event.respond("لطفاً لینک یا نام کاربری گروه/کانال را برای ترک کردن ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'left_link_handler'
        self.tbot.handlers['left_account'] = account

    async def left_link_handler(self, event):
        """
        Handle the leave link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}")
                return
            
            account = self.tbot.handlers.get('left_account')
            if not account:
                await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            # Leave the group/channel
            entity = await account.get_entity(link)
            await account.leave_chat(entity)
            account_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
            await event.respond(f"✅ با موفقیت از {link} با حساب {account_name} خارج شدید.")
            
            # Cleanup
            self.tbot.handlers.pop('left_account', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error leaving group/channel: {e}")
            await event.respond(f"❌ خطا در ترک کردن گروه/کانال: {str(e)}")
            # Cleanup on error
            self.tbot.handlers.pop('left_account', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def block(self, account, event):
        """
        Perform the block action - block a user.
        """
        await event.respond("لطفاً شناسه کاربری یا نام کاربری فرد مورد نظر را برای بلاک کردن ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'block_user_handler'
        self.tbot.handlers['block_account'] = account

    async def block_user_handler(self, event):
        """
        Handle the block user input.
        """
        try:
            user_input = event.message.text.strip()
            account = self.tbot.handlers.get('block_account')
            if not account:
                await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            # Block the user
            from telethon.tl.functions.contacts import BlockRequest
            entity = await account.get_entity(user_input)
            await account(BlockRequest(entity))
            account_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
            await event.respond(f"✅ کاربر {user_input} با حساب {account_name} با موفقیت بلاک شد.")
            
            # Cleanup
            self.tbot.handlers.pop('block_account', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            await event.respond(f"❌ خطا در بلاک کردن کاربر: {str(e)}")
            # Cleanup on error
            self.tbot.handlers.pop('block_account', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def send_pv(self, account, event):
        """
        Perform the send_pv action - send a private message to a user.
        """
        await event.respond("لطفاً شناسه کاربری یا نام کاربری فرد مورد نظر را برای ارسال پیام ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'send_pv_user_handler'
        self.tbot.handlers['send_pv_account'] = account

    async def send_pv_user_handler(self, event):
        """
        Handle the send_pv user input.
        """
        try:
            user_input = event.message.text.strip()
            self.tbot.handlers['send_pv_user'] = user_input
            await event.respond("لطفاً متن پیام مورد نظر را ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'send_pv_message_handler'
        except Exception as e:
            logger.error(f"Error in send_pv_user_handler: {e}")
            await event.respond("❌ خطا در پردازش اطلاعات کاربر. لطفاً دوباره تلاش کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('send_pv_account', None)
            self.tbot.handlers.pop('send_pv_user', None)

    async def send_pv_message_handler(self, event):
        """
        Handle the send_pv message input.
        """
        try:
            message = event.message.text.strip()
            
            # Validate message text
            is_valid, error_msg = InputValidator.validate_message_text(message)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            account = self.tbot.handlers.get('send_pv_account')
            user_input = self.tbot.handlers.get('send_pv_user')
            if not account:
                await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            # Send the private message
            entity = await account.get_entity(user_input)
            await account.send_message(entity, message)
            account_name = account.session.filename if hasattr(account, 'session') and hasattr(account.session, 'filename') else 'Unknown'
            await event.respond(f"✅ پیام با موفقیت به {user_input} با حساب {account_name} ارسال شد.")
            
            # Cleanup
            self.tbot.handlers.pop('send_pv_account', None)
            self.tbot.handlers.pop('send_pv_user', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error sending private message: {e}")
            await event.respond(f"❌ خطا در ارسال پیام خصوصی: {str(e)}")
            # Cleanup on error
            self.tbot.handlers.pop('send_pv_account', None)
            self.tbot.handlers.pop('send_pv_user', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def comment(self, account, event) -> None:
        """
        Initiate comment operation for individual account.
        
        Prompts user for post/message link to comment on.
        
        Args:
            account: TelegramClient instance to use
            event: Telegram event
        """
        await event.respond("لطفاً لینک پست یا پیام را برای کامنت ارسال کنید:")
        async with self.tbot._conversations_lock:
            self.tbot._conversations[event.chat_id] = 'comment_link_handler'
        self.tbot.handlers['comment_account'] = account

    async def comment_link_handler(self, event):
        """
        Handle the comment link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            self.tbot.handlers['comment_link'] = link
            await event.respond("لطفاً نظر خود را وارد کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'comment_text_handler'
        except Exception as e:
            logger.error(f"Error in comment_link_handler: {e}")
            await event.respond("❌ خطا در پردازش لینک. لطفاً دوباره تلاش کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('comment_account', None)
            self.tbot.handlers.pop('comment_link', None)

    async def comment_text_handler(self, event):
        """
        Handle the comment text input.
        """
        try:
            comment_text = event.message.text.strip()
            
            # Validate comment text
            is_valid, error_msg = InputValidator.validate_message_text(comment_text)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            account = self.tbot.handlers.get('comment_account')
            link = self.tbot.handlers.get('comment_link')
            is_bulk = self.tbot.handlers.get('comment_is_bulk', False)
            
            if is_bulk:
                # This is a bulk operation
                num_accounts = self.tbot.handlers.get('comment_num_accounts')
                if num_accounts is None:
                    await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    return
                
                async with self.tbot.active_clients_lock:
                    accounts = list(self.tbot.active_clients.values())[:num_accounts]
                
                # Parse link once
                chat_entity, message_id = await self.parse_telegram_link(link, accounts[0] if accounts else None)
                
                if chat_entity is None or message_id is None:
                    raise ValueError(f"Failed to parse comment link: {link}")
                
                # Comment with all accounts
                success_count = 0
                error_count = 0
                revoked_sessions = []
                
                async def comment_with_account(acc):
                    nonlocal success_count, error_count
                    session_name = None
                    try:
                        session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                    except (AttributeError, Exception):
                        session_name = 'Unknown'
                    
                    async with self.operation_semaphore:
                        try:
                            # Resolve entity if needed
                            peer = chat_entity
                            if isinstance(peer, str):
                                peer = await acc.get_entity(peer)
                            elif isinstance(peer, int) and peer < 0:
                                peer = await acc.get_entity(peer)
                            
                            await acc.send_message(peer, comment_text, reply_to=message_id)
                            async with self._counter_lock:
                                success_count += 1
                            await asyncio.sleep(random.uniform(2, 5))
                        except FloodWaitError as e:
                            async with self._counter_lock:
                                error_count += 1
                            logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                            await asyncio.sleep(e.seconds)
                        except (SessionRevokedError, ValueError) as e:
                            error_msg = str(e).lower()
                            if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                                async with self._counter_lock:
                                    error_count += 1
                                    revoked_sessions.append(session_name)
                                logger.warning(f"Session revoked for account {session_name}: {e}")
                            else:
                                async with self._counter_lock:
                                    error_count += 1
                                logger.error(f"Error posting comment with account {session_name}: {e}")
                        except Exception as e:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error posting comment with account {session_name}: {e}")
                
                tasks = [comment_with_account(acc) for acc in accounts]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Remove revoked sessions from active_clients
                if revoked_sessions:
                    await self._remove_revoked_sessions(revoked_sessions)
                
                # Report results
                if error_count == 0:
                    await event.respond(f"✅ با موفقیت نظر با {success_count} حساب ارسال شد.")
                else:
                    msg = f"⚠️ نظر با {success_count} حساب ارسال شد. {error_count} حساب با خطا مواجه شد."
                    if revoked_sessions:
                        msg += f"\n⚠️ {len(revoked_sessions)} حساب revoked شده و حذف شدند."
                    await event.respond(msg)
                
                # Cleanup
                self.tbot.handlers.pop('comment_link', None)
                self.tbot.handlers.pop('comment_num_accounts', None)
                self.tbot.handlers.pop('comment_is_bulk', None)
            else:
                # Individual operation
                account = self.tbot.handlers.get('comment_account')
                if not account:
                    await event.respond("❌ حساب یافت نشد. لطفاً دوباره شروع کنید.")
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    return
                
                chat_entity, message_id = await self.parse_telegram_link(link, account)
                
                if chat_entity is None or message_id is None:
                    raise ValueError(f"Failed to parse comment link: {link}")
                
                # Resolve entity if needed
                if isinstance(chat_entity, str):
                    chat_entity = await account.get_entity(chat_entity)
                
                # Send the comment
                await account.send_message(chat_entity, comment_text, reply_to=message_id)
                await event.respond(f"✅ با موفقیت نظر ارسال شد.")
            
            # Cleanup
            self.tbot.handlers.pop('comment_account', None)
            self.tbot.handlers.pop('comment_link', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error posting comment: {e}")
            await event.respond(f"❌ خطا در ارسال نظر: {str(e)}")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            # Cleanup
            self.tbot.handlers.pop('comment_account', None)
            self.tbot.handlers.pop('comment_link', None)
            self.tbot.handlers.pop('comment_num_accounts', None)
            self.tbot.handlers.pop('comment_is_bulk', None)

    # ==================== Bulk Operation Handlers ====================
    
    async def bulk_poll(self, event, num_accounts):
        """
        Handle bulk poll operation - ask for link and option once, then vote with all accounts.
        """
        try:
            self.tbot.handlers['poll_num_accounts'] = num_accounts
            self.tbot.handlers['poll_is_bulk'] = True
            await event.respond("لطفاً لینک نظرسنجی را ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'poll_link_handler'
        except Exception as e:
            logger.error(f"Error in bulk_poll: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk poll.")
            self.tbot.handlers.pop('poll_num_accounts', None)
            self.tbot.handlers.pop('poll_is_bulk', None)
    
    async def bulk_join(self, event, num_accounts):
        """
        Handle bulk join operation - ask for link once, then join with all accounts.
        """
        try:
            await event.respond("لطفاً لینک گروه یا کانال را برای عضویت ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_join_link_handler'
            self.tbot.handlers['join_num_accounts'] = num_accounts
        except Exception as e:
            logger.error(f"Error in bulk_join: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk join.")
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
                await event.respond(f"❌ {error_msg}")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                self.tbot.handlers.pop('join_num_accounts', None)
                return
            
            num_accounts = self.tbot.handlers.get('join_num_accounts')
            if num_accounts is None:
                await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            revoked_sessions = []
            
            async def join_with_account(acc):
                nonlocal success_count, error_count
                session_name = None
                try:
                    session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                except (AttributeError, Exception):
                    session_name = 'Unknown'
                
                async with self.operation_semaphore:
                    try:
                        await acc.join_chat(link)
                        async with self._counter_lock:
                            success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except FloodWaitError as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (SessionRevokedError, ValueError) as e:
                        error_msg = str(e).lower()
                        if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                            async with self._counter_lock:
                                error_count += 1
                                revoked_sessions.append(session_name)
                            logger.warning(f"Session revoked for account {session_name}: {e}")
                        else:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error joining with account {session_name}: {e}")
                    except Exception as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.error(f"Error joining with account {session_name}: {e}")
            
            tasks = [join_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Remove revoked sessions from active_clients
            if revoked_sessions:
                await self._remove_revoked_sessions(revoked_sessions)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت با {success_count} حساب عضو شدید.")
            else:
                msg = f"⚠️ با {success_count} حساب عضو شدید. {error_count} حساب با خطا مواجه شد."
                if revoked_sessions:
                    msg += f"\n⚠️ {len(revoked_sessions)} حساب revoked شده و حذف شدند."
                await event.respond(msg)
            
            # Cleanup
            self.tbot.handlers.pop('join_num_accounts', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error in bulk_join_link_handler: {e}")
            await event.respond(f"❌ خطا در عضویت گروه/کانال: {str(e)}")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('join_num_accounts', None)
    
    async def bulk_leave(self, event, num_accounts):
        """
        Handle bulk leave operation - ask for link once, then leave with all accounts.
        """
        try:
            await event.respond("لطفاً لینک گروه یا کانال را برای ترک کردن ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_leave_link_handler'
            self.tbot.handlers['leave_num_accounts'] = num_accounts
        except Exception as e:
            logger.error(f"Error in bulk_leave: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk leave.")
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
                await event.respond(f"❌ {error_msg}")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                self.tbot.handlers.pop('leave_num_accounts', None)
                return
            
            num_accounts = self.tbot.handlers.get('leave_num_accounts')
            if num_accounts is None:
                await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            revoked_sessions = []
            
            async def leave_with_account(acc):
                nonlocal success_count, error_count
                session_name = None
                try:
                    session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                except (AttributeError, Exception):
                    session_name = 'Unknown'
                
                async with self.operation_semaphore:
                    try:
                        entity = await acc.get_entity(link)
                        await acc.leave_chat(entity)
                        async with self._counter_lock:
                            success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except FloodWaitError as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (SessionRevokedError, ValueError) as e:
                        error_msg = str(e).lower()
                        if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                            async with self._counter_lock:
                                error_count += 1
                                revoked_sessions.append(session_name)
                            logger.warning(f"Session revoked for account {session_name}: {e}")
                        else:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error leaving group/channel with account {session_name}: {e}")
                    except Exception as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.error(f"Error leaving group/channel with account {session_name}: {e}")
            
            tasks = [leave_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Remove revoked sessions from active_clients
            if revoked_sessions:
                await self._remove_revoked_sessions(revoked_sessions)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت با {success_count} حساب از گروه/کانال خارج شدید.")
            else:
                msg = f"⚠️ با {success_count} حساب از گروه/کانال خارج شدید. {error_count} حساب با خطا مواجه شد."
                if revoked_sessions:
                    msg += f"\n⚠️ {len(revoked_sessions)} حساب revoked شده و حذف شدند."
                await event.respond(msg)
            
            # Cleanup
            self.tbot.handlers.pop('leave_num_accounts', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error in bulk_leave_link_handler: {e}")
            await event.respond(f"❌ خطا در ترک کردن گروه/کانال: {str(e)}")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('leave_num_accounts', None)
    
    async def bulk_block(self, event, num_accounts):
        """
        Handle bulk block operation - ask for user once, then block with all accounts.
        """
        try:
            await event.respond("لطفاً شناسه کاربری یا نام کاربری فرد مورد نظر را برای بلاک کردن ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_block_user_handler'
            self.tbot.handlers['block_num_accounts'] = num_accounts
        except Exception as e:
            logger.error(f"Error in bulk_block: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk block.")
            self.tbot.handlers.pop('block_num_accounts', None)
    
    async def bulk_block_user_handler(self, event):
        """
        Handle bulk block user input.
        """
        try:
            user_input = event.message.text.strip()
            
            num_accounts = self.tbot.handlers.get('block_num_accounts')
            if num_accounts is None:
                await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            revoked_sessions = []
            
            async def block_with_account(acc):
                nonlocal success_count, error_count
                session_name = None
                try:
                    session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                except (AttributeError, Exception):
                    session_name = 'Unknown'
                
                async with self.operation_semaphore:
                    try:
                        from telethon.tl.functions.contacts import BlockRequest
                        entity = await acc.get_entity(user_input)
                        await acc(BlockRequest(entity))
                        async with self._counter_lock:
                            success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except FloodWaitError as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (SessionRevokedError, ValueError) as e:
                        error_msg = str(e).lower()
                        if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                            async with self._counter_lock:
                                error_count += 1
                                revoked_sessions.append(session_name)
                            logger.warning(f"Session revoked for account {session_name}: {e}")
                        else:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error blocking user with account {session_name}: {e}")
                    except Exception as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.error(f"Error blocking user with account {session_name}: {e}")
            
            tasks = [block_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Remove revoked sessions from active_clients
            if revoked_sessions:
                await self._remove_revoked_sessions(revoked_sessions)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت کاربر {user_input} با {success_count} حساب بلاک شد.")
            else:
                msg = f"⚠️ کاربر {user_input} با {success_count} حساب بلاک شد. {error_count} حساب با خطا مواجه شد."
                if revoked_sessions:
                    msg += f"\n⚠️ {len(revoked_sessions)} حساب revoked شده و حذف شدند."
                await event.respond(msg)
            
            # Cleanup
            self.tbot.handlers.pop('block_num_accounts', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error in bulk_block_user_handler: {e}")
            await event.respond(f"❌ خطا در بلاک کردن کاربر: {str(e)}")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('block_num_accounts', None)
    
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
                await event.respond(f"❌ لطفاً یک عدد معتبر بین 1 و {total_accounts} وارد کنید.")
                return

            num_accounts = int(user_input)
            logger.info(f"Parsed number: {num_accounts}")

            # Validate range
            if num_accounts < 1 or num_accounts > total_accounts:
                logger.warning(f"Number {num_accounts} is out of range 1-{total_accounts}")
                await event.respond(f"❌ لطفاً یک عدد بین 1 و {total_accounts} وارد کنید.")
                return

            # Store the number and proceed to ask for username
            logger.info("Proceeding to ask for username")
            self.tbot.handlers['send_pv_num_accounts'] = num_accounts
            await event.respond("لطفاً شناسه کاربری یا نام کاربری فرد مورد نظر را برای ارسال پیام ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_send_pv_user_handler'
        except Exception as e:
            logger.error(f"Error in bulk_send_pv_account_count_handler: {e}")
            await event.respond("❌ خطا در پردازش تعداد حساب‌ها. لطفاً دوباره تلاش کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)

    async def bulk_send_pv(self, event, num_accounts):
        """
        Handle bulk send_pv operation - ask for user and message once, then send with all accounts.
        """
        try:
            await event.respond("لطفاً شناسه کاربری یا نام کاربری فرد مورد نظر را برای ارسال پیام ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_send_pv_user_handler'
            self.tbot.handlers['send_pv_num_accounts'] = num_accounts
        except Exception as e:
            logger.error(f"Error in bulk_send_pv: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk send_pv.")
            self.tbot.handlers.pop('send_pv_num_accounts', None)
    
    async def bulk_send_pv_user_handler(self, event) -> None:
        """
        Handle bulk send_pv user input and prompt for message text.
        
        Args:
            event: Telegram NewMessage event containing user ID/username
        """
        try:
            user_input = event.message.text.strip()
            self.tbot.handlers['send_pv_user'] = user_input
            await event.respond("لطفاً متن پیام مورد نظر را ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'bulk_send_pv_message_handler'
        except Exception as e:
            logger.error(f"Error in bulk_send_pv_user_handler: {e}")
            await event.respond("❌ خطا در پردازش اطلاعات کاربر. لطفاً دوباره تلاش کنید.")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('send_pv_num_accounts', None)
            self.tbot.handlers.pop('send_pv_user', None)
    
    async def bulk_send_pv_message_handler(self, event):
        """
        Handle bulk send_pv message input.
        """
        try:
            message = event.message.text.strip()
            
            # Validate message text
            is_valid, error_msg = InputValidator.validate_message_text(message)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nلطفاً دوباره تلاش کنید.")
                return
            
            user_input = self.tbot.handlers.get('send_pv_user')
            num_accounts = self.tbot.handlers.get('send_pv_num_accounts')
            if num_accounts is None:
                await event.respond("❌ تعداد حساب‌ها یافت نشد. لطفاً دوباره شروع کنید.")
                async with self.tbot._conversations_lock:
                    self.tbot._conversations.pop(event.chat_id, None)
                return
            
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            revoked_sessions = []
            
            async def send_pv_with_account(acc):
                nonlocal success_count, error_count
                session_name = None
                try:
                    session_name = acc.session.filename if hasattr(acc, 'session') and hasattr(acc.session, 'filename') else 'Unknown'
                except (AttributeError, Exception):
                    session_name = 'Unknown'
                
                async with self.operation_semaphore:
                    try:
                        entity = await acc.get_entity(user_input)
                        await acc.send_message(entity, message)
                        async with self._counter_lock:
                            success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except FloodWaitError as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.warning(f"FloodWaitError for account {session_name}: waiting {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (SessionRevokedError, ValueError) as e:
                        error_msg = str(e).lower()
                        if 'session' in error_msg or 'revoked' in error_msg or 'not logged in' in error_msg:
                            async with self._counter_lock:
                                error_count += 1
                                revoked_sessions.append(session_name)
                            logger.warning(f"Session revoked for account {session_name}: {e}")
                        else:
                            async with self._counter_lock:
                                error_count += 1
                            logger.error(f"Error sending private message with account {session_name}: {e}")
                    except Exception as e:
                        async with self._counter_lock:
                            error_count += 1
                        logger.error(f"Error sending private message with account {session_name}: {e}")
            
            tasks = [send_pv_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Remove revoked sessions from active_clients
            if revoked_sessions:
                await self._remove_revoked_sessions(revoked_sessions)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت پیام با {success_count} حساب ارسال شد.")
            else:
                msg = f"⚠️ پیام با {success_count} حساب ارسال شد. {error_count} حساب با خطا مواجه شد."
                if revoked_sessions:
                    msg += f"\n⚠️ {len(revoked_sessions)} حساب revoked شده و حذف شدند."
                await event.respond(msg)
            
            # Cleanup
            self.tbot.handlers.pop('send_pv_num_accounts', None)
            self.tbot.handlers.pop('send_pv_user', None)
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error in bulk_send_pv_message_handler: {e}")
            await event.respond(f"❌ خطا در ارسال پیام خصوصی: {str(e)}")
            async with self.tbot._conversations_lock:
                self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('send_pv_num_accounts', None)
            self.tbot.handlers.pop('send_pv_user', None)
    
    async def bulk_comment(self, event, num_accounts):
        """
        Handle bulk comment operation - ask for link and text once, then comment with all accounts.
        """
        try:
            self.tbot.handlers['comment_num_accounts'] = num_accounts
            self.tbot.handlers['comment_is_bulk'] = True
            await event.respond("لطفاً لینک پست یا پیام را برای کامنت ارسال کنید:")
            async with self.tbot._conversations_lock:
                self.tbot._conversations[event.chat_id] = 'comment_link_handler'
        except Exception as e:
            logger.error(f"Error in bulk_comment: {e}")
            await event.respond("❌ خطا در شروع عملیات bulk comment.")
            self.tbot.handlers.pop('comment_num_accounts', None)
            self.tbot.handlers.pop('comment_is_bulk', None)
    
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
                await asyncio.sleep(2)
                
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

