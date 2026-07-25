"""
CLI interface for Telegram Panel operations.
Allows running operations without Telegram bot.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from src.config import ConfigManager, API_ID, API_HASH, CLIENTS_JSON_PATH
from src.actions import Actions
from src.client import SessionManager
from src.validation import InputValidator
from src.utils import get_session_name, sanitize_session_name
from src.logger import setup_logging

logger = logging.getLogger(__name__)


class CLIManager:
    """CLI Manager for Telegram Panel operations without bot."""
    
    def __init__(self):
        """Initialize CLI Manager."""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.active_clients = {}
        self.active_clients_lock = asyncio.Lock()
        self.session_manager = None
        self.actions = None
    
    async def initialize(self):
        """Initialize clients and actions."""
        try:
            # Create a minimal tbot-like object for Actions
            class MinimalTbot:
                def __init__(self, config, active_clients, active_clients_lock, config_manager):
                    self.config = config
                    self.active_clients = active_clients
                    self.active_clients_lock = active_clients_lock
                    self.config_manager = config_manager
                    self.handlers = {}
                    self._conversations = {}
                    self._conversations_lock = asyncio.Lock()
            
            minimal_tbot = MinimalTbot(
                self.config,
                self.active_clients,
                self.active_clients_lock,
                self.config_manager
            )
            
            self.session_manager = SessionManager(
                self.config,
                self.active_clients,
                minimal_tbot
            )
            
            self.actions = Actions(minimal_tbot)
            
            # Load and start saved clients
            await self.session_manager.start_saved_clients()
            
            logger.info("CLI Manager initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing CLI Manager: {e}")
            raise
    
    async def list_accounts(self) -> List[str]:
        """List all available accounts."""
        async with self.active_clients_lock:
            return list(self.active_clients.keys())
    
    async def add_account(self, phone_number: str) -> bool:
        """Add a new account via CLI."""
        try:
            # Validate phone number
            is_valid, error_msg = InputValidator.validate_phone_number(phone_number)
            if not is_valid:
                print(f"Error: {error_msg}")
                return False
            
            # Sanitize session name
            try:
                session_name = sanitize_session_name(phone_number)
            except ValueError as e:
                print(f"Error: Invalid phone number format: {e}")
                return False
            
            # Check if account already exists
            if session_name in self.active_clients:
                print(f"Account {session_name} already exists")
                return False
            
            # Create client
            client = TelegramClient(session_name, API_ID, API_HASH)
            
            print(f"Connecting to Telegram for {phone_number}...")
            await client.connect()
            
            if not await client.is_user_authorized():
                print("Sending code request...")
                await client.send_code_request(phone_number)
                
                code = input("Enter the code you received: ").strip()
                
                try:
                    await client.sign_in(phone_number, code)
                except SessionPasswordNeededError:
                    password = input("Enter your 2FA password: ").strip()
                    await client.sign_in(password=password)
            
            # Save account
            async with self.active_clients_lock:
                self.active_clients[session_name] = client
            
            # Update config
            if 'clients' not in self.config:
                self.config['clients'] = {}
            self.config['clients'][session_name] = {
                'phone': phone_number,
                'enabled': True
            }
            self.config_manager.save_config(self.config)
            
            print(f"Account {session_name} added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding account: {e}")
            print(f"Error: {e}")
            return False
    
    async def remove_account(self, session_name: str) -> bool:
        """Remove an account."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                
                client = self.active_clients[session_name]
                if client.is_connected():
                    await client.disconnect()
                del self.active_clients[session_name]
            
            # Remove from config
            if session_name in self.config.get('clients', {}):
                del self.config['clients'][session_name]
                self.config_manager.save_config(self.config)
            
            print(f"Account {session_name} removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error removing account: {e}")
            print(f"Error: {e}")
            return False
    
    async def reaction(self, session_name: str, link: str, reaction: str) -> bool:
        """Apply reaction to a message."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            await self.actions.apply_reaction(account, link, reaction)
            print(f"Reaction {reaction} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error applying reaction: {e}")
            print(f"Error: {e}")
            return False
    
    async def vote_poll(self, session_name: str, link: str, option: int) -> bool:
        """Vote in a poll."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            # Parse link
            chat_entity, message_id = await self.actions.parse_telegram_link(link, account)
            if chat_entity is None or message_id is None:
                print(f"Error: Failed to parse link: {link}")
                return False
            
            # Resolve entity
            from src.utils import resolve_entity
            chat_entity = await resolve_entity(chat_entity, account)
            
            # Get message to verify it's a poll
            message = await account.get_messages(chat_entity, ids=message_id)
            if message is None:
                print("Error: Message not found")
                return False
            if not message.poll:
                print("Error: The provided link does not point to a poll")
                return False
            
            # Vote
            from telethon.tl.functions.messages import SendVoteRequest
            option_index = option - 1  # Convert to 0-based
            await account(SendVoteRequest(
                peer=chat_entity,
                msg_id=message_id,
                options=[bytes([option_index])]
            ))
            
            print(f"Voted for option {option} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error voting in poll: {e}")
            print(f"Error: {e}")
            return False
    
    async def join_chat(self, session_name: str, link: str) -> bool:
        """Join a group or channel."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            # Try join_chat first, fallback to JoinChannelRequest
            try:
                if hasattr(account, 'join_chat'):
                    await account.join_chat(link)
                else:
                    from src.utils import resolve_entity
                    from telethon.tl.functions.channels import JoinChannelRequest
                    entity = await resolve_entity(link, account)
                    await account(JoinChannelRequest(entity))
            except AttributeError:
                from src.utils import resolve_entity
                from telethon.tl.functions.channels import JoinChannelRequest
                entity = await resolve_entity(link, account)
                await account(JoinChannelRequest(entity))
            
            print(f"Successfully joined {link}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining chat: {e}")
            print(f"Error: {e}")
            return False
    
    async def leave_chat(self, session_name: str, link: str) -> bool:
        """Leave a group or channel."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            entity = await account.get_entity(link)
            await account.delete_dialog(entity)
            
            print(f"Successfully left {link}")
            return True
            
        except Exception as e:
            logger.error(f"Error leaving chat: {e}")
            print(f"Error: {e}")
            return False
    
    async def block_user(self, session_name: str, user_input: str) -> bool:
        """Block a user."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            from src.utils import resolve_entity
            from telethon.tl.functions.contacts import BlockRequest
            entity = await resolve_entity(user_input, account)
            await account(BlockRequest(entity))
            
            print(f"User {user_input} blocked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            print(f"Error: {e}")
            return False
    
    async def send_message(self, session_name: str, user_input: str, message: str) -> bool:
        """Send a private message."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            from src.utils import resolve_entity
            entity = await resolve_entity(user_input, account)
            await account.send_message(entity, message)
            
            print(f"Message sent successfully to {user_input}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            print(f"Error: {e}")
            return False
    
    async def comment(self, session_name: str, link: str, comment_text: str) -> bool:
        """Post a comment on a message."""
        try:
            async with self.active_clients_lock:
                if session_name not in self.active_clients:
                    print(f"Account {session_name} not found")
                    return False
                account = self.active_clients[session_name]
            
            if not account.is_connected():
                await account.connect()
            
            # Parse link
            chat_entity, message_id = await self.actions.parse_telegram_link(link, account)
            if chat_entity is None or message_id is None:
                print(f"Error: Failed to parse link: {link}")
                return False
            
            # Resolve entity
            from src.utils import resolve_entity
            chat_entity = await resolve_entity(chat_entity, account)
            
            # Send comment
            await account.send_message(chat_entity, comment_text, reply_to=message_id)
            
            print("Comment sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error posting comment: {e}")
            print(f"Error: {e}")
            return False
    
    async def bulk_operation(self, operation: str, num_accounts: int, **kwargs) -> dict:
        """Execute bulk operation."""
        try:
            async with self.active_clients_lock:
                accounts = list(self.active_clients.values())[:num_accounts]
            
            if not accounts:
                print("No accounts available")
                return {'success': 0, 'error': 0}
            
            # Validate accounts are connected
            valid_accounts = []
            for acc in accounts:
                try:
                    if acc.is_connected():
                        valid_accounts.append(acc)
                    else:
                        await acc.connect()
                        valid_accounts.append(acc)
                except Exception as e:
                    logger.warning(f"Error connecting account {get_session_name(acc)}: {e}")
            
            if not valid_accounts:
                print("No connected accounts available")
                return {'success': 0, 'error': 0}
            
            success_count = 0
            error_count = 0
            
            for account in valid_accounts:
                try:
                    session_name = get_session_name(account)
                    
                    if operation == 'reaction':
                        await self.actions.apply_reaction(account, kwargs['link'], kwargs['reaction'])
                    elif operation == 'vote':
                        chat_entity, message_id = await self.actions.parse_telegram_link(kwargs['link'], account)
                        if chat_entity and message_id:
                            from src.utils import resolve_entity
                            from telethon.tl.functions.messages import SendVoteRequest
                            chat_entity = await resolve_entity(chat_entity, account)
                            option_index = kwargs['option'] - 1
                            await account(SendVoteRequest(
                                peer=chat_entity,
                                msg_id=message_id,
                                options=[bytes([option_index])]
                            ))
                    elif operation == 'join':
                        if hasattr(account, 'join_chat'):
                            await account.join_chat(kwargs['link'])
                        else:
                            from src.utils import resolve_entity
                            from telethon.tl.functions.channels import JoinChannelRequest
                            entity = await resolve_entity(kwargs['link'], account)
                            await account(JoinChannelRequest(entity))
                    elif operation == 'leave':
                        from src.utils import resolve_entity
                        entity = await resolve_entity(kwargs['link'], account)
                        await account.delete_dialog(entity)
                    elif operation == 'block':
                        from src.utils import resolve_entity
                        from telethon.tl.functions.contacts import BlockRequest
                        entity = await resolve_entity(kwargs['user_input'], account)
                        await account(BlockRequest(entity))
                    elif operation == 'send_pv':
                        from src.utils import resolve_entity
                        entity = await resolve_entity(kwargs['user_input'], account)
                        await account.send_message(entity, kwargs['message'])
                    elif operation == 'comment':
                        chat_entity, message_id = await self.actions.parse_telegram_link(kwargs['link'], account)
                        if chat_entity and message_id:
                            from src.utils import resolve_entity
                            chat_entity = await resolve_entity(chat_entity, account)
                            await account.send_message(chat_entity, kwargs['comment_text'], reply_to=message_id)
                    
                    success_count += 1
                    print(f"✓ {session_name}: Success")
                    
                except Exception as e:
                    error_count += 1
                    print(f"✗ {session_name}: Error - {e}")
            
            print(f"\nBulk operation completed: {success_count} success, {error_count} errors")
            return {'success': success_count, 'error': error_count}
            
        except Exception as e:
            logger.error(f"Error in bulk operation: {e}")
            print(f"Error: {e}")
            return {'success': 0, 'error': 0}
    
    async def cleanup(self):
        """Cleanup and disconnect all clients."""
        async with self.active_clients_lock:
            for client in self.active_clients.values():
                try:
                    if client.is_connected():
                        await client.disconnect()
                except Exception as e:
                    logger.debug(f"Failed to disconnect client: {e}")


# CLI Commands using click
try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False
    # Fallback to argparse if click is not available
    import argparse


def run_command(operation):
    """
    Run a single manager operation inside one event loop.

    Telethon clients (and the asyncio locks) created in ``initialize`` are bound
    to the event loop they were created on, so initialization, the operation and
    cleanup must all share the same loop. Using a fresh ``asyncio.run`` per step
    would attach the clients to a closed loop and fail at runtime.
    """
    async def _runner():
        manager = CLIManager()
        await manager.initialize()
        try:
            return await operation(manager)
        finally:
            await manager.cleanup()
    return asyncio.run(_runner())


if HAS_CLICK:

    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        """Telegram Panel CLI - Manage Telegram accounts and operations."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
    
    @cli.command()
    def list_accounts():
        """List all available accounts."""
        accounts = run_command(lambda m: m.list_accounts())
        if accounts:
            print("\nAvailable accounts:")
            for i, acc in enumerate(accounts, 1):
                print(f"  {i}. {acc}")
        else:
            print("No accounts available")
    
    @cli.command()
    @click.argument('phone_number')
    def add_account(phone_number):
        """Add a new account."""
        run_command(lambda m: m.add_account(phone_number))
    
    @cli.command()
    @click.argument('session_name')
    def remove_account(session_name):
        """Remove an account."""
        run_command(lambda m: m.remove_account(session_name))
    
    @cli.group()
    def individual():
        """Individual operations on a single account."""
        pass
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    @click.argument('reaction', type=click.Choice(['👍', '❤️', '😂', '😮', '😢', '😡']))
    def reaction(session_name, link, reaction):
        """Apply reaction to a message."""
        run_command(lambda m: m.reaction(session_name, link, reaction))
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    @click.argument('option', type=int)
    def vote(session_name, link, option):
        """Vote in a poll."""
        run_command(lambda m: m.vote_poll(session_name, link, option))
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    def join(session_name, link):
        """Join a group or channel."""
        run_command(lambda m: m.join_chat(session_name, link))
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    def leave(session_name, link):
        """Leave a group or channel."""
        run_command(lambda m: m.leave_chat(session_name, link))
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('user_input')
    def block(session_name, user_input):
        """Block a user."""
        run_command(lambda m: m.block_user(session_name, user_input))
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('user_input')
    @click.argument('message')
    def send_pv(session_name, user_input, message):
        """Send a private message."""
        run_command(lambda m: m.send_message(session_name, user_input, message))
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    @click.argument('comment_text')
    def comment(session_name, link, comment_text):
        """Post a comment on a message."""
        run_command(lambda m: m.comment(session_name, link, comment_text))
    
    @cli.group()
    def bulk():
        """Bulk operations on multiple accounts."""
        pass
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    @click.argument('reaction', type=click.Choice(['👍', '❤️', '😂', '😮', '😢', '😡']))
    def reaction(num_accounts, link, reaction):
        """Apply reaction with multiple accounts."""
        run_command(lambda m: m.bulk_operation('reaction', num_accounts, link=link, reaction=reaction))
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    @click.argument('option', type=int)
    def vote(num_accounts, link, option):
        """Vote in a poll with multiple accounts."""
        run_command(lambda m: m.bulk_operation('vote', num_accounts, link=link, option=option))
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    def join(num_accounts, link):
        """Join a group/channel with multiple accounts."""
        run_command(lambda m: m.bulk_operation('join', num_accounts, link=link))
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    def leave(num_accounts, link):
        """Leave a group/channel with multiple accounts."""
        run_command(lambda m: m.bulk_operation('leave', num_accounts, link=link))
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('user_input')
    def block(num_accounts, user_input):
        """Block a user with multiple accounts."""
        run_command(lambda m: m.bulk_operation('block', num_accounts, user_input=user_input))
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('user_input')
    @click.argument('message')
    def send_pv(num_accounts, user_input, message):
        """Send private message with multiple accounts."""
        run_command(lambda m: m.bulk_operation('send_pv', num_accounts, user_input=user_input, message=message))
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    @click.argument('comment_text')
    def comment(num_accounts, link, comment_text):
        """Post comment with multiple accounts."""
        run_command(lambda m: m.bulk_operation('comment', num_accounts, link=link, comment_text=comment_text))
    
    def main():
        """Main CLI entry point."""
        setup_logging()
        try:
            cli()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            logger.error(f"CLI error: {e}", exc_info=True)
            print(f"Error: {e}")
            sys.exit(1)

else:
    # Fallback to argparse
    REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '😡']

    INDIVIDUAL_COMMANDS = {
        'reaction': ('Apply reaction', [('session_name', {}), ('link', {}), ('reaction', {'choices': REACTIONS})]),
        'vote': ('Vote in poll', [('session_name', {}), ('link', {}), ('option', {'type': int})]),
        'join': ('Join chat', [('session_name', {}), ('link', {})]),
        'leave': ('Leave chat', [('session_name', {}), ('link', {})]),
        'block': ('Block user', [('session_name', {}), ('user_input', {})]),
        'send-pv': ('Send private message', [('session_name', {}), ('user_input', {}), ('message', {})]),
        'comment': ('Post comment', [('session_name', {}), ('link', {}), ('comment_text', {})]),
    }

    BULK_COMMANDS = {
        'reaction': ('Bulk reaction', [('num_accounts', {'type': int}), ('link', {}), ('reaction', {'choices': REACTIONS})]),
        'vote': ('Bulk vote', [('num_accounts', {'type': int}), ('link', {}), ('option', {'type': int})]),
        'join': ('Bulk join', [('num_accounts', {'type': int}), ('link', {})]),
        'leave': ('Bulk leave', [('num_accounts', {'type': int}), ('link', {})]),
        'block': ('Bulk block', [('num_accounts', {'type': int}), ('user_input', {})]),
        'send-pv': ('Bulk send private message', [('num_accounts', {'type': int}), ('user_input', {}), ('message', {})]),
        'comment': ('Bulk comment', [('num_accounts', {'type': int}), ('link', {}), ('comment_text', {})]),
    }

    TOP_LEVEL_OPS = {
        'list-accounts': lambda m, a: m.list_accounts(),
        'add-account': lambda m, a: m.add_account(a.phone_number),
        'remove-account': lambda m, a: m.remove_account(a.session_name),
    }

    INDIVIDUAL_OPS = {
        'reaction': lambda m, a: m.reaction(a.session_name, a.link, a.reaction),
        'vote': lambda m, a: m.vote_poll(a.session_name, a.link, a.option),
        'join': lambda m, a: m.join_chat(a.session_name, a.link),
        'leave': lambda m, a: m.leave_chat(a.session_name, a.link),
        'block': lambda m, a: m.block_user(a.session_name, a.user_input),
        'send-pv': lambda m, a: m.send_message(a.session_name, a.user_input, a.message),
        'comment': lambda m, a: m.comment(a.session_name, a.link, a.comment_text),
    }

    BULK_OPS = {
        'reaction': lambda m, a: m.bulk_operation('reaction', a.num_accounts, link=a.link, reaction=a.reaction),
        'vote': lambda m, a: m.bulk_operation('vote', a.num_accounts, link=a.link, option=a.option),
        'join': lambda m, a: m.bulk_operation('join', a.num_accounts, link=a.link),
        'leave': lambda m, a: m.bulk_operation('leave', a.num_accounts, link=a.link),
        'block': lambda m, a: m.bulk_operation('block', a.num_accounts, user_input=a.user_input),
        'send-pv': lambda m, a: m.bulk_operation('send_pv', a.num_accounts, user_input=a.user_input, message=a.message),
        'comment': lambda m, a: m.bulk_operation('comment', a.num_accounts, link=a.link, comment_text=a.comment_text),
    }

    def _add_group(subparsers, name, help_text, commands):
        group = subparsers.add_parser(name, help=help_text)
        group_subparsers = group.add_subparsers(dest='operation')
        for command, (command_help, arguments) in commands.items():
            command_parser = group_subparsers.add_parser(command, help=command_help)
            for argument, kwargs in arguments:
                command_parser.add_argument(argument, **kwargs)

    def _build_parser():
        parser = argparse.ArgumentParser(description='Telegram Panel CLI')
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        subparsers.add_parser('list-accounts', help='List all accounts')
        subparsers.add_parser('add-account', help='Add a new account').add_argument('phone_number', help='Phone number')
        subparsers.add_parser('remove-account', help='Remove an account').add_argument('session_name', help='Session name')

        _add_group(subparsers, 'individual', 'Individual operations', INDIVIDUAL_COMMANDS)
        _add_group(subparsers, 'bulk', 'Bulk operations', BULK_COMMANDS)
        return parser

    def _resolve_operation(args):
        """Return a callable running the requested command, or None."""
        if args.command in TOP_LEVEL_OPS:
            return TOP_LEVEL_OPS[args.command]
        table = {'individual': INDIVIDUAL_OPS, 'bulk': BULK_OPS}.get(args.command)
        if table is None:
            return None
        return table.get(getattr(args, 'operation', None))

    def main():
        """Main CLI entry point using argparse."""
        setup_logging()
        parser = _build_parser()
        args = parser.parse_args()

        operation = _resolve_operation(args) if args.command else None
        if operation is None:
            parser.print_help()
            return

        try:
            result = run_command(lambda m: operation(m, args))
            if args.command == 'list-accounts':
                if result:
                    print("\nAvailable accounts:")
                    for i, acc in enumerate(result, 1):
                        print(f"  {i}. {acc}")
                else:
                    print("No accounts available")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            logger.error(f"CLI error: {e}", exc_info=True)
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()

