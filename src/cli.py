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

from src.Config import ConfigManager, API_ID, API_HASH, CLIENTS_JSON_PATH
from src.actions import Actions
from src.Client import SessionManager
from src.Validation import InputValidator
from src.utils import get_session_name, sanitize_session_name
from src.Logger import setup_logging

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
            
            from src.utils import resolve_entity
            entity = await account.get_entity(link)
            await account.leave_chat(entity)
            
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
                        await account.leave_chat(entity)
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
                except Exception:
                    pass


# CLI Commands using click
try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False
    # Fallback to argparse if click is not available
    import argparse


if HAS_CLICK:
    _manager_instance = None
    
    def get_manager():
        """Get or create CLI manager instance."""
        global _manager_instance
        if _manager_instance is None:
            _manager_instance = CLIManager()
            asyncio.run(_manager_instance.initialize())
        return _manager_instance
    
    @click.group(invoke_without_command=True)
    @click.pass_context
    def cli(ctx):
        """Telegram Panel CLI - Manage Telegram accounts and operations."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
    
    @cli.command()
    def list_accounts():
        """List all available accounts."""
        manager = get_manager()
        try:
            accounts = asyncio.run(manager.list_accounts())
            if accounts:
                print("\nAvailable accounts:")
                for i, acc in enumerate(accounts, 1):
                    print(f"  {i}. {acc}")
            else:
                print("No accounts available")
        finally:
            asyncio.run(manager.cleanup())
    
    @cli.command()
    @click.argument('phone_number')
    def add_account(phone_number):
        """Add a new account."""
        manager = get_manager()
        try:
            asyncio.run(manager.add_account(phone_number))
        finally:
            asyncio.run(manager.cleanup())
    
    @cli.command()
    @click.argument('session_name')
    def remove_account(session_name):
        """Remove an account."""
        manager = get_manager()
        try:
            asyncio.run(manager.remove_account(session_name))
        finally:
            asyncio.run(manager.cleanup())
    
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
        manager = get_manager()
        try:
            asyncio.run(manager.reaction(session_name, link, reaction))
        finally:
            asyncio.run(manager.cleanup())
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    @click.argument('option', type=int)
    def vote(session_name, link, option):
        """Vote in a poll."""
        manager = get_manager()
        try:
            asyncio.run(manager.vote_poll(session_name, link, option))
        finally:
            asyncio.run(manager.cleanup())
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    def join(session_name, link):
        """Join a group or channel."""
        manager = get_manager()
        try:
            asyncio.run(manager.join_chat(session_name, link))
        finally:
            asyncio.run(manager.cleanup())
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    def leave(session_name, link):
        """Leave a group or channel."""
        manager = get_manager()
        try:
            asyncio.run(manager.leave_chat(session_name, link))
        finally:
            asyncio.run(manager.cleanup())
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('user_input')
    def block(session_name, user_input):
        """Block a user."""
        manager = get_manager()
        try:
            asyncio.run(manager.block_user(session_name, user_input))
        finally:
            asyncio.run(manager.cleanup())
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('user_input')
    @click.argument('message')
    def send_pv(session_name, user_input, message):
        """Send a private message."""
        manager = get_manager()
        try:
            asyncio.run(manager.send_message(session_name, user_input, message))
        finally:
            asyncio.run(manager.cleanup())
    
    @individual.command()
    @click.argument('session_name')
    @click.argument('link')
    @click.argument('comment_text')
    def comment(session_name, link, comment_text):
        """Post a comment on a message."""
        manager = get_manager()
        try:
            asyncio.run(manager.comment(session_name, link, comment_text))
        finally:
            asyncio.run(manager.cleanup())
    
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
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('reaction', num_accounts, link=link, reaction=reaction))
        finally:
            asyncio.run(manager.cleanup())
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    @click.argument('option', type=int)
    def vote(num_accounts, link, option):
        """Vote in a poll with multiple accounts."""
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('vote', num_accounts, link=link, option=option))
        finally:
            asyncio.run(manager.cleanup())
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    def join(num_accounts, link):
        """Join a group/channel with multiple accounts."""
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('join', num_accounts, link=link))
        finally:
            asyncio.run(manager.cleanup())
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    def leave(num_accounts, link):
        """Leave a group/channel with multiple accounts."""
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('leave', num_accounts, link=link))
        finally:
            asyncio.run(manager.cleanup())
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('user_input')
    def block(num_accounts, user_input):
        """Block a user with multiple accounts."""
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('block', num_accounts, user_input=user_input))
        finally:
            asyncio.run(manager.cleanup())
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('user_input')
    @click.argument('message')
    def send_pv(num_accounts, user_input, message):
        """Send private message with multiple accounts."""
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('send_pv', num_accounts, user_input=user_input, message=message))
        finally:
            asyncio.run(manager.cleanup())
    
    @bulk.command()
    @click.argument('num_accounts', type=int)
    @click.argument('link')
    @click.argument('comment_text')
    def comment(num_accounts, link, comment_text):
        """Post comment with multiple accounts."""
        manager = get_manager()
        try:
            asyncio.run(manager.bulk_operation('comment', num_accounts, link=link, comment_text=comment_text))
        finally:
            asyncio.run(manager.cleanup())
    
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
    def main():
        """Main CLI entry point using argparse."""
        setup_logging()
        parser = argparse.ArgumentParser(description='Telegram Panel CLI')
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Account management
        subparsers.add_parser('list-accounts', help='List all accounts')
        add_parser = subparsers.add_parser('add-account', help='Add a new account')
        add_parser.add_argument('phone_number', help='Phone number')
        remove_parser = subparsers.add_parser('remove-account', help='Remove an account')
        remove_parser.add_argument('session_name', help='Session name')
        
        # Individual operations
        individual_parser = subparsers.add_parser('individual', help='Individual operations')
        individual_subparsers = individual_parser.add_subparsers(dest='operation')
        
        reaction_parser = individual_subparsers.add_parser('reaction', help='Apply reaction')
        reaction_parser.add_argument('session_name')
        reaction_parser.add_argument('link')
        reaction_parser.add_argument('reaction', choices=['👍', '❤️', '😂', '😮', '😢', '😡'])
        
        vote_parser = individual_subparsers.add_parser('vote', help='Vote in poll')
        vote_parser.add_argument('session_name')
        vote_parser.add_argument('link')
        vote_parser.add_argument('option', type=int)
        
        join_parser = individual_subparsers.add_parser('join', help='Join chat')
        join_parser.add_argument('session_name')
        join_parser.add_argument('link')
        
        leave_parser = individual_subparsers.add_parser('leave', help='Leave chat')
        leave_parser.add_argument('session_name')
        leave_parser.add_argument('link')
        
        block_parser = individual_subparsers.add_parser('block', help='Block user')
        block_parser.add_argument('session_name')
        block_parser.add_argument('user_input')
        
        send_pv_parser = individual_subparsers.add_parser('send-pv', help='Send private message')
        send_pv_parser.add_argument('session_name')
        send_pv_parser.add_argument('user_input')
        send_pv_parser.add_argument('message')
        
        comment_parser = individual_subparsers.add_parser('comment', help='Post comment')
        comment_parser.add_argument('session_name')
        comment_parser.add_argument('link')
        comment_parser.add_argument('comment_text')
        
        # Bulk operations
        bulk_parser = subparsers.add_parser('bulk', help='Bulk operations')
        bulk_subparsers = bulk_parser.add_subparsers(dest='operation')
        
        bulk_reaction_parser = bulk_subparsers.add_parser('reaction', help='Bulk reaction')
        bulk_reaction_parser.add_argument('num_accounts', type=int)
        bulk_reaction_parser.add_argument('link')
        bulk_reaction_parser.add_argument('reaction', choices=['👍', '❤️', '😂', '😮', '😢', '😡'])
        
        bulk_vote_parser = bulk_subparsers.add_parser('vote', help='Bulk vote')
        bulk_vote_parser.add_argument('num_accounts', type=int)
        bulk_vote_parser.add_argument('link')
        bulk_vote_parser.add_argument('option', type=int)
        
        bulk_join_parser = bulk_subparsers.add_parser('join', help='Bulk join')
        bulk_join_parser.add_argument('num_accounts', type=int)
        bulk_join_parser.add_argument('link')
        
        bulk_leave_parser = bulk_subparsers.add_parser('leave', help='Bulk leave')
        bulk_leave_parser.add_argument('num_accounts', type=int)
        bulk_leave_parser.add_argument('link')
        
        bulk_block_parser = bulk_subparsers.add_parser('block', help='Bulk block')
        bulk_block_parser.add_argument('num_accounts', type=int)
        bulk_block_parser.add_argument('user_input')
        
        bulk_send_pv_parser = bulk_subparsers.add_parser('send-pv', help='Bulk send private message')
        bulk_send_pv_parser.add_argument('num_accounts', type=int)
        bulk_send_pv_parser.add_argument('user_input')
        bulk_send_pv_parser.add_argument('message')
        
        bulk_comment_parser = bulk_subparsers.add_parser('comment', help='Bulk comment')
        bulk_comment_parser.add_argument('num_accounts', type=int)
        bulk_comment_parser.add_argument('link')
        bulk_comment_parser.add_argument('comment_text')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        manager = CLIManager()
        asyncio.run(manager.initialize())
        
        try:
            if args.command == 'list-accounts':
                accounts = asyncio.run(manager.list_accounts())
                if accounts:
                    print("\nAvailable accounts:")
                    for i, acc in enumerate(accounts, 1):
                        print(f"  {i}. {acc}")
                else:
                    print("No accounts available")
            
            elif args.command == 'add-account':
                asyncio.run(manager.add_account(args.phone_number))
            
            elif args.command == 'remove-account':
                asyncio.run(manager.remove_account(args.session_name))
            
            elif args.command == 'individual':
                if args.operation == 'reaction':
                    asyncio.run(manager.reaction(args.session_name, args.link, args.reaction))
                elif args.operation == 'vote':
                    asyncio.run(manager.vote_poll(args.session_name, args.link, args.option))
                elif args.operation == 'join':
                    asyncio.run(manager.join_chat(args.session_name, args.link))
                elif args.operation == 'leave':
                    asyncio.run(manager.leave_chat(args.session_name, args.link))
                elif args.operation == 'block':
                    asyncio.run(manager.block_user(args.session_name, args.user_input))
                elif args.operation == 'send-pv':
                    asyncio.run(manager.send_message(args.session_name, args.user_input, args.message))
                elif args.operation == 'comment':
                    asyncio.run(manager.comment(args.session_name, args.link, args.comment_text))
            
            elif args.command == 'bulk':
                if args.operation == 'reaction':
                    asyncio.run(manager.bulk_operation('reaction', args.num_accounts, link=args.link, reaction=args.reaction))
                elif args.operation == 'vote':
                    asyncio.run(manager.bulk_operation('vote', args.num_accounts, link=args.link, option=args.option))
                elif args.operation == 'join':
                    asyncio.run(manager.bulk_operation('join', args.num_accounts, link=args.link))
                elif args.operation == 'leave':
                    asyncio.run(manager.bulk_operation('leave', args.num_accounts, link=args.link))
                elif args.operation == 'block':
                    asyncio.run(manager.bulk_operation('block', args.num_accounts, user_input=args.user_input))
                elif args.operation == 'send-pv':
                    asyncio.run(manager.bulk_operation('send_pv', args.num_accounts, user_input=args.user_input, message=args.message))
                elif args.operation == 'comment':
                    asyncio.run(manager.bulk_operation('comment', args.num_accounts, link=args.link, comment_text=args.comment_text))
            
            asyncio.run(manager.cleanup())
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
        except Exception as e:
            logger.error(f"CLI error: {e}", exc_info=True)
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()

