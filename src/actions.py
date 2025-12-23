import logging
import random
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import SendVoteRequest, SendReactionRequest
try:
    from telethon.tl.types import ReactionEmoji
except ImportError:
    # Fallback for older Telethon versions
    from telethon.tl import types
    ReactionEmoji = getattr(types, 'ReactionEmoji', None)
from src.Config import CHANNEL_ID
from src.Validation import InputValidator

logger = logging.getLogger(__name__)

# Concurrency limit for bulk operations to avoid rate limiting
MAX_CONCURRENT_OPERATIONS = 3

class Actions:
    def __init__(self, tbot):
        self.tbot = tbot
        self.operation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

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

    async def prompt_group_action(self, event, action_name):
        """
        Prompt the user to enter the number of accounts to be used for the group action.
        """
        async with self.tbot.active_clients_lock:
            total_accounts = len(self.tbot.active_clients)
        
        message = f"There are {total_accounts} accounts available. Please choose how many accounts (from 1 to {total_accounts}) will perform the {action_name} action."
        buttons = [Button.inline(str(i), f"{action_name}_{i}") for i in range(1, total_accounts + 1)]
        await event.respond(message, buttons=buttons)

    async def prompt_individual_action(self, event, action_name):
        """
        Show a list of account names as clickable buttons and prompt the user to select which account should perform the action.
        """
        async with self.tbot.active_clients_lock:
            sessions = list(self.tbot.active_clients.keys())
        
        buttons = [Button.inline(session, f"{action_name}_{session}") for session in sessions]
        await event.respond("Please select an account to perform the action:", buttons=buttons)

    async def handle_group_action(self, event, action_name, num_accounts):
        """
        Handle the group action by calling the respective function for all selected accounts.
        Uses semaphore to limit concurrent operations and avoid rate limiting.
        """
        async with self.tbot.active_clients_lock:
            accounts = list(self.tbot.active_clients.values())[:num_accounts]
        
        async def execute_action(account):
            """Execute action with concurrency limit"""
            async with self.operation_semaphore:
                try:
                    await getattr(self, action_name)(account, event)
                    # Add delay between operations to avoid rate limiting
                    await asyncio.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.error(f"Error executing {action_name} for account {account.session.filename}: {e}")
        
        # Execute all actions concurrently with semaphore limiting
        tasks = [execute_action(account) for account in accounts]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def handle_individual_action(self, event, action_name, session):
        """
        Handle the individual action by calling the respective function for the selected account.
        """
        async with self.tbot.active_clients_lock:
            account = self.tbot.active_clients.get(session)
        
        if account:
            await getattr(self, action_name)(account, event)
        else:
            await event.respond(f"Account {session} not found.")

    async def reaction(self, account, event):
        """
        Perform the reaction action.
        """
        # Step 1: Ask for the link to the message
        await event.respond("Please provide the link to the message where the reaction will be applied.")
        self.tbot._conversations[event.chat_id] = 'reaction_link_handler'

    async def reaction_link_handler(self, event):
        """
        Handle the link input for the reaction action.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nPlease try again.")
                return
            
            await event.respond("Please select a reaction:", buttons=[
                Button.inline("👍", b'reaction_thumbsup'),
                Button.inline("❤️", b'reaction_heart'),
                Button.inline("😂", b'reaction_laugh'),
                Button.inline("😮", b'reaction_wow'),
                Button.inline("😢", b'reaction_sad'),
                Button.inline("😡", b'reaction_angry')
            ])
            self.tbot._conversations[event.chat_id] = 'reaction_select_handler'
            self.tbot.handlers['reaction_link'] = link
        except Exception as e:
            logger.error(f"Error in reaction_link_handler: {e}")
            await event.respond("Error processing link. Please try again.")
            self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('reaction_link', None)

    async def reaction_select_handler(self, event):
        """
        Handle the reaction selection.
        """
        # This handler should be added to callback handler, not message handler
        # It's triggered by inline button clicks
        reaction_map = {
            'reaction_thumbsup': '👍',
            'reaction_heart': '❤️',
            'reaction_laugh': '😂',
            'reaction_wow': '😮',
            'reaction_sad': '😢',
            'reaction_angry': '😡'
        }
        
        data = event.data.decode() if hasattr(event, 'data') else event.message.text.strip()
        reaction = reaction_map.get(data, data)
        
        async with self.tbot.active_clients_lock:
            total_accounts = len(self.tbot.active_clients)
        
        await event.respond(f"Please specify the number of reactions (from 1 to {total_accounts}):")
        self.tbot._conversations[event.chat_id] = 'reaction_count_handler'
        self.tbot.handlers['reaction'] = reaction

    async def reaction_count_handler(self, event):
        """
        Handle the number of reactions input.
        """
        try:
            count = int(event.message.text.strip())
            
            async with self.tbot.active_clients_lock:
                total_clients = len(self.tbot.active_clients)
                if count < 1 or count > total_clients:
                    raise ValueError(f"Invalid number of reactions. Must be between 1 and {total_clients}.")
                accounts = list(self.tbot.active_clients.values())[:count]
            
            link = self.tbot.handlers['reaction_link']
            reaction = self.tbot.handlers['reaction']
            
            # Use semaphore to limit concurrent reactions
            async def apply_reaction_with_limit(account):
                async with self.operation_semaphore:
                    try:
                        await self.apply_reaction(account, link, reaction)
                        await asyncio.sleep(random.uniform(2, 5))
                    except Exception as e:
                        logger.error(f"Error applying reaction with account {account.session.filename}: {e}")
            
            # Execute all reactions with concurrency control
            tasks = [apply_reaction_with_limit(account) for account in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            await event.respond(f"Applied {reaction} reaction using {count} accounts.")
            
            # Cleanup
            self.tbot.handlers.pop('reaction_link', None)
            self.tbot.handlers.pop('reaction', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except ValueError as e:
            await event.respond(f"Error: {e}. Please enter a valid number of reactions.")
            # Don't reset conversation state - let it stay to retry

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

    async def poll(self, account, event):
        """
        Perform the poll action - vote on a poll.
        """
        await event.respond("Please provide the link to the poll:")
        self.tbot._conversations[event.chat_id] = 'poll_link_handler'
        self.tbot.handlers['poll_account'] = account

    async def poll_link_handler(self, event):
        """
        Handle the poll link input.
        """
        try:
            link = event.message.text.strip()
            
            # Validate link
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nPlease try again.")
                return
            
            self.tbot.handlers['poll_link'] = link
            await event.respond("Please enter the option number you want to vote for (e.g., 1, 2, 3):")
            self.tbot._conversations[event.chat_id] = 'poll_option_handler'
        except Exception as e:
            logger.error(f"Error in poll_link_handler: {e}")
            await event.respond("Error processing link. Please try again.")
            self.tbot._conversations.pop(event.chat_id, None)
            self.tbot.handlers.pop('poll_account', None)
            self.tbot.handlers.pop('poll_link', None)

    async def poll_option_handler(self, event):
        """
        Handle the poll option selection.
        """
        try:
            # Validate poll option
            is_valid, error_msg, option_num = InputValidator.validate_poll_option(event.message.text.strip())
            if not is_valid:
                await event.respond(f"❌ {error_msg}\nPlease try again.")
                return
            
            option = option_num - 1  # Convert to 0-based index
            account = self.tbot.handlers.get('poll_account')
            link = self.tbot.handlers.get('poll_link')
            
            # Parse the link to get chat and message IDs
            parts = link.split('/')
            if 't.me/c/' in link:
                chat_id = int('-100' + parts[-2])
                message_id = int(parts[-1])
            else:
                chat_username = parts[-2]
                message_id = int(parts[-1])
                chat_id = chat_username
            
            # Get the poll message
            message = await account.get_messages(chat_id, ids=message_id)
            if message.poll:
                await account(SendVoteRequest(
                    peer=chat_id,
                    msg_id=message_id,
                    options=[bytes([option])]
                ))
                await event.respond(f"Successfully voted option {option + 1} using account {account.session.filename}")
            else:
                await event.respond("The provided link does not point to a poll.")
            
            # Cleanup
            self.tbot.handlers.pop('poll_account', None)
            self.tbot.handlers.pop('poll_link', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error voting on poll: {e}")
            await event.respond(f"Error voting on poll: {str(e)}")
            self.tbot._conversations.pop(event.chat_id, None)

    async def join(self, account, event):
        """
        Perform the join action - join a group or channel.
        """
        await event.respond("Please provide the group/channel link or username to join:")
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
            
            # Join the group/channel
            await account.join_chat(link)
            await event.respond(f"Successfully joined {link} using account {account.session.filename}")
            
            # Cleanup
            self.tbot.handlers.pop('join_account', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error joining group/channel: {e}")
            await event.respond(f"Error joining group/channel: {str(e)}")
            self.tbot._conversations.pop(event.chat_id, None)

    async def left(self, account, event):
        """
        Perform the left action - leave a group or channel.
        """
        await event.respond("Please provide the group/channel link or username to leave:")
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
            
            # Leave the group/channel
            entity = await account.get_entity(link)
            await account.leave_chat(entity)
            await event.respond(f"Successfully left {link} using account {account.session.filename}")
            
            # Cleanup
            self.tbot.handlers.pop('left_account', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error leaving group/channel: {e}")
            await event.respond(f"Error leaving group/channel: {str(e)}")
            self.tbot._conversations.pop(event.chat_id, None)

    async def block(self, account, event):
        """
        Perform the block action - block a user.
        """
        await event.respond("Please provide the user ID or username to block:")
        self.tbot._conversations[event.chat_id] = 'block_user_handler'
        self.tbot.handlers['block_account'] = account

    async def block_user_handler(self, event):
        """
        Handle the block user input.
        """
        try:
            user_input = event.message.text.strip()
            account = self.tbot.handlers.get('block_account')
            
            # Block the user
            from telethon.tl.functions.contacts import BlockRequest
            entity = await account.get_entity(user_input)
            await account(BlockRequest(entity))
            await event.respond(f"Successfully blocked user {user_input} using account {account.session.filename}")
            
            # Cleanup
            self.tbot.handlers.pop('block_account', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            await event.respond(f"Error blocking user: {str(e)}")
            self.tbot._conversations.pop(event.chat_id, None)

    async def send_pv(self, account, event):
        """
        Perform the send_pv action - send a private message to a user.
        """
        await event.respond("Please provide the user ID or username to send a message to:")
        self.tbot._conversations[event.chat_id] = 'send_pv_user_handler'
        self.tbot.handlers['send_pv_account'] = account

    async def send_pv_user_handler(self, event):
        """
        Handle the send_pv user input.
        """
        try:
            user_input = event.message.text.strip()
            self.tbot.handlers['send_pv_user'] = user_input
            await event.respond("Please enter the message you want to send:")
            self.tbot._conversations[event.chat_id] = 'send_pv_message_handler'
        except Exception as e:
            logger.error(f"Error in send_pv_user_handler: {e}")
            await event.respond("Error processing user input. Please try again.")
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
                await event.respond(f"❌ {error_msg}\nPlease try again.")
                return
            
            account = self.tbot.handlers.get('send_pv_account')
            user_input = self.tbot.handlers.get('send_pv_user')
            
            # Send the private message
            entity = await account.get_entity(user_input)
            await account.send_message(entity, message)
            await event.respond(f"Successfully sent message to {user_input} using account {account.session.filename}")
            
            # Cleanup
            self.tbot.handlers.pop('send_pv_account', None)
            self.tbot.handlers.pop('send_pv_user', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error sending private message: {e}")
            await event.respond(f"Error sending private message: {str(e)}")
            self.tbot._conversations.pop(event.chat_id, None)

    async def comment(self, account, event):
        """
        Perform the comment action - comment on a post/message.
        """
        await event.respond("Please provide the link to the post/message:")
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
                await event.respond(f"❌ {error_msg}\nPlease try again.")
                return
            
            self.tbot.handlers['comment_link'] = link
            await event.respond("Please enter your comment:")
            self.tbot._conversations[event.chat_id] = 'comment_text_handler'
        except Exception as e:
            logger.error(f"Error in comment_link_handler: {e}")
            await event.respond("Error processing link. Please try again.")
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
                await event.respond(f"❌ {error_msg}\nPlease try again.")
                return
            
            account = self.tbot.handlers.get('comment_account')
            link = self.tbot.handlers.get('comment_link')
            
            # Parse the link to get chat and message IDs
            parts = link.split('/')
            if 't.me/c/' in link:
                chat_id = int('-100' + parts[-2])
                message_id = int(parts[-1])
            else:
                chat_username = parts[-2]
                message_id = int(parts[-1])
                chat_id = chat_username
            
            # Send the comment
            await account.send_message(chat_id, comment_text, reply_to=message_id)
            await event.respond(f"Successfully posted comment using account {account.session.filename}")
            
            # Cleanup
            self.tbot.handlers.pop('comment_account', None)
            self.tbot.handlers.pop('comment_link', None)
            self.tbot._conversations.pop(event.chat_id, None)
            
        except Exception as e:
            logger.error(f"Error posting comment: {e}")
            await event.respond(f"Error posting comment: {str(e)}")
            self.tbot._conversations.pop(event.chat_id, None)


                    self.tbot.handlers.pop('poll_link', None)
                    self.tbot.handlers.pop('poll_num_accounts', None)
                    self.tbot.handlers.pop('poll_is_bulk', None)
                    async with self.tbot._conversations_lock:
                        self.tbot._conversations.pop(event.chat_id, None)
                    return
                
                # Vote with all accounts
                success_count = 0
                error_count = 0
                
                async def vote_with_account(acc):
                    nonlocal success_count, error_count
                    async with self.operation_semaphore:
                        try:
                            # Resolve entity if needed
                            peer = chat_entity
                            if isinstance(peer, str):
                                peer = await acc.get_entity(peer)
                            elif isinstance(peer, int) and peer < 0:
                                peer = await acc.get_entity(peer)
                            
                            await acc(SendVoteRequest(
                                peer=peer,
                                msg_id=message_id,
                                options=[bytes([option])]
                            ))
                            success_count += 1
                            await asyncio.sleep(random.uniform(2, 5))
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error voting on poll with account {acc.session.filename if hasattr(acc, 'session') else 'Unknown'}: {e}")
                
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
                    await event.respond(f"✅ با موفقیت به گزینه {option_num} رای داده شد.")
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

    async def comment(self, account, event):
        """
        Perform the comment action - comment on a post/message.
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
                async with self.tbot.active_clients_lock:
                    accounts = list(self.tbot.active_clients.values())[:num_accounts]
                
                # Parse link once
                chat_entity, message_id = await self.parse_telegram_link(link, accounts[0] if accounts else None)
                
                if chat_entity is None or message_id is None:
                    raise ValueError(f"Failed to parse comment link: {link}")
                
                # Comment with all accounts
                success_count = 0
                error_count = 0
                
                async def comment_with_account(acc):
                    nonlocal success_count, error_count
                    async with self.operation_semaphore:
                        try:
                            # Resolve entity if needed
                            peer = chat_entity
                            if isinstance(peer, str):
                                peer = await acc.get_entity(peer)
                            elif isinstance(peer, int) and peer < 0:
                                peer = await acc.get_entity(peer)
                            
                            await acc.send_message(peer, comment_text, reply_to=message_id)
                            success_count += 1
                            await asyncio.sleep(random.uniform(2, 5))
                        except Exception as e:
                            error_count += 1
                            logger.error(f"Error posting comment with account {acc.session.filename if hasattr(acc, 'session') else 'Unknown'}: {e}")
                
                tasks = [comment_with_account(acc) for acc in accounts]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Report results
                if error_count == 0:
                    await event.respond(f"✅ با موفقیت نظر با {success_count} حساب ارسال شد.")
                else:
                    await event.respond(f"⚠️ نظر با {success_count} حساب ارسال شد. {error_count} حساب با خطا مواجه شد.")
                
                # Cleanup
                self.tbot.handlers.pop('comment_link', None)
                self.tbot.handlers.pop('comment_num_accounts', None)
                self.tbot.handlers.pop('comment_is_bulk', None)
            else:
                # Individual operation
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
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            
            async def join_with_account(acc):
                nonlocal success_count, error_count
                async with self.operation_semaphore:
                    try:
                        await acc.join_chat(link)
                        success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error joining with account {acc.session.filename if hasattr(acc, 'session') else 'Unknown'}: {e}")
            
            tasks = [join_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت با {success_count} حساب عضو شدید.")
            else:
                await event.respond(f"⚠️ با {success_count} حساب عضو شدید. {error_count} حساب با خطا مواجه شد.")
            
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
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            
            async def block_with_account(acc):
                nonlocal success_count, error_count
                async with self.operation_semaphore:
                    try:
                        from telethon.tl.functions.contacts import BlockRequest
                        entity = await acc.get_entity(user_input)
                        await acc(BlockRequest(entity))
                        success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error blocking user with account {acc.session.filename if hasattr(acc, 'session') else 'Unknown'}: {e}")
            
            tasks = [block_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت کاربر {user_input} با {success_count} حساب بلاک شد.")
            else:
                await event.respond(f"⚠️ کاربر {user_input} با {success_count} حساب بلاک شد. {error_count} حساب با خطا مواجه شد.")
            
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
    
    async def bulk_send_pv_user_handler(self, event):
        """
        Handle bulk send_pv user input.
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
            async with self.tbot.active_clients_lock:
                accounts = list(self.tbot.active_clients.values())[:num_accounts]
            
            success_count = 0
            error_count = 0
            
            async def send_pv_with_account(acc):
                nonlocal success_count, error_count
                async with self.operation_semaphore:
                    try:
                        entity = await acc.get_entity(user_input)
                        await acc.send_message(entity, message)
                        success_count += 1
                        await asyncio.sleep(random.uniform(2, 5))
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error sending private message with account {acc.session.filename if hasattr(acc, 'session') else 'Unknown'}: {e}")
            
            tasks = [send_pv_with_account(acc) for acc in accounts]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Report results
            if error_count == 0:
                await event.respond(f"✅ با موفقیت پیام با {success_count} حساب ارسال شد.")
            else:
                await event.respond(f"⚠️ پیام با {success_count} حساب ارسال شد. {error_count} حساب با خطا مواجه شد.")
            
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

