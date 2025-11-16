import logging
import random
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import SendVoteRequest
from src.Config import CHANNEL_ID
from src.Validation import InputValidator

logger = logging.getLogger(__name__)

# Concurrency limit for bulk operations to avoid rate limiting
MAX_CONCURRENT_OPERATIONS = 3

class Actions:
    def __init__(self, tbot):
        self.tbot = tbot
        self.operation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

    async def prompt_group_action(self, event, action_name):
        """
        Prompt the user to enter the number of accounts to be used for the group action.
        """
        total_accounts = len(self.tbot.active_clients)
        message = f"There are {total_accounts} accounts available. Please choose how many accounts (from 1 to {total_accounts}) will perform the {action_name} action."
        buttons = [Button.inline(str(i), f"{action_name}_{i}") for i in range(1, total_accounts + 1)]
        await event.respond(message, buttons=buttons)

    async def prompt_individual_action(self, event, action_name):
        """
        Show a list of account names as clickable buttons and prompt the user to select which account should perform the action.
        """
        buttons = [Button.inline(session, f"{action_name}_{session}") for session in self.tbot.active_clients.keys()]
        await event.respond("Please select an account to perform the action:", buttons=buttons)

    async def handle_group_action(self, event, action_name, num_accounts):
        """
        Handle the group action by calling the respective function for all selected accounts.
        Uses semaphore to limit concurrent operations and avoid rate limiting.
        """
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
            if count < 1 or count > len(self.tbot.active_clients):
                raise ValueError("Invalid number of reactions.")
            link = self.tbot.handlers['reaction_link']
            reaction = self.tbot.handlers['reaction']
            accounts = list(self.tbot.active_clients.values())[:count]
            
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
        """
        try:
            await account.send_message(link, reaction)
            logger.info(f"Applied {reaction} reaction using account {account.session.filename}")
        except Exception as e:
            logger.error(f"Error applying reaction: {e}")

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
        link = event.message.text.strip()
        
        # Validate link
        is_valid, error_msg = InputValidator.validate_telegram_link(link)
        if not is_valid:
            await event.respond(f"❌ {error_msg}\nPlease try again.")
            return
        
        self.tbot.handlers['poll_link'] = link
        await event.respond("Please enter the option number you want to vote for (e.g., 1, 2, 3):")
        self.tbot._conversations[event.chat_id] = 'poll_option_handler'

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
        user_input = event.message.text.strip()
        self.tbot.handlers['send_pv_user'] = user_input
        await event.respond("Please enter the message you want to send:")
        self.tbot._conversations[event.chat_id] = 'send_pv_message_handler'

    async def send_pv_message_handler(self, event):
        """
        Handle the send_pv message input.
        """
        try:
            message = event.message.text.strip()
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
        link = event.message.text.strip()
        self.tbot.handlers['comment_link'] = link
        await event.respond("Please enter your comment:")
        self.tbot._conversations[event.chat_id] = 'comment_text_handler'

    async def comment_text_handler(self, event):
        """
        Handle the comment text input.
        """
        try:
            comment_text = event.message.text.strip()
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

