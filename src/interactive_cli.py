"""
Interactive CLI interface with beautiful, minimal UI.
Provides Telegram bot-like interface in terminal.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from src.Config import ConfigManager, API_ID, API_HASH
from src.actions import Actions
from src.Client import SessionManager
from src.Validation import InputValidator
from src.utils import get_session_name, sanitize_session_name
from src.Logger import setup_logging

logger = logging.getLogger(__name__)

try:
    from prompt_toolkit import prompt, PromptSession
    from prompt_toolkit.shortcuts import prompt as pt_prompt, confirm, radiolist_dialog
    from prompt_toolkit.formatted_text import HTML, ANSI
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, Container
    from prompt_toolkit.widgets import Box, Button, Frame, Label, TextArea, RadioList
    from prompt_toolkit.application import Application
    from prompt_toolkit.styles import Style
    from prompt_toolkit.completion import Completer, Completion
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich import box
    from rich.live import Live
    from rich.layout import Layout as RichLayout
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.status import Status
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class InteractiveCLI:
    """Interactive CLI with beautiful, minimal UI."""
    
    # Beautiful color scheme
    COLORS = {
        'primary': '#00D4FF',
        'secondary': '#FF6B9D',
        'success': '#00FF88',
        'warning': '#FFB800',
        'error': '#FF4444',
        'info': '#00D4FF',
        'muted': '#888888',
        'bg': '#1A1A1A',
        'fg': '#FFFFFF',
    }
    
    def __init__(self):
        """Initialize Interactive CLI."""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.active_clients = {}
        self.active_clients_lock = asyncio.Lock()
        self.session_manager = None
        self.actions = None
        self.console = None
        
        # Use global variables for library availability
        try:
            self.has_prompt_toolkit = HAS_PROMPT_TOOLKIT
        except NameError:
            self.has_prompt_toolkit = False
        try:
            self.has_rich = HAS_RICH
        except NameError:
            self.has_rich = False
            
        if self.has_rich:
            self.console = Console(force_terminal=True, width=80)
    
    async def initialize(self):
        """Initialize clients and actions."""
        try:
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
            
            await self.session_manager.start_saved_clients()
            
            logger.info("Interactive CLI initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Interactive CLI: {e}")
            raise
    
    def _clear_screen(self):
        """Clear terminal screen."""
        if self.has_rich and self.console:
            self.console.clear()
        else:
            os.system('clear' if os.name != 'nt' else 'cls')
    
    def _print_header(self, title: str = "Telegram Panel", clear: bool = True):
        """Print beautiful header with optional screen clear."""
        if clear:
            self._clear_screen()
        if self.has_rich and self.console:
            header = Panel(
                Align.center(Text(title, style="bold cyan")),
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            self.console.print(header)
        else:
            print(f"\n{'═' * 60}")
            print(f"  {title}".center(60))
            print(f"{'═' * 60}\n")
    
    def _print_success(self, message: str, wait: bool = True):
        """Print success message."""
        if self.has_rich and self.console:
            self.console.print(f"[bold green]✓[/bold green] {message}")
        else:
            print(f"✓ {message}")
        if wait:
            input("\nPress Enter to continue...")
            self._clear_screen()
    
    def _print_error(self, message: str, wait: bool = True):
        """Print error message."""
        if self.has_rich and self.console:
            self.console.print(f"[bold red]✗[/bold red] {message}")
        else:
            print(f"✗ {message}")
        if wait:
            input("\nPress Enter to continue...")
            self._clear_screen()
    
    def _print_info(self, message: str, wait: bool = False):
        """Print info message."""
        if self.has_rich and self.console:
            self.console.print(f"[cyan]ℹ[/cyan] {message}")
        else:
            print(f"ℹ {message}")
        if wait:
            input("\nPress Enter to continue...")
            self._clear_screen()
    
    async def _show_loading(self, message: str, coro):
        """Show loading indicator while executing coroutine."""
        if self.has_rich and self.console:
            with self.console.status(f"[cyan]{message}[/cyan]", spinner="dots"):
                result = await coro
                return result
        else:
            print(f"⏳ {message}...")
            result = await coro
            return result
    
    async def _confirm_action(self, message: str, default: bool = False) -> bool:
        """Ask for confirmation before action."""
        if self.has_rich and self.console:
            return Confirm.ask(f"[yellow]⚠[/yellow] {message}", default=default)
        else:
            default_text = "Y/n" if default else "y/N"
            response = input(f"⚠ {message} ({default_text}): ").strip().lower()
            if not response:
                return default
            return response in ['y', 'yes']
    
    async def _show_loading(self, message: str, coro):
        """Show loading indicator while executing coroutine."""
        if self.has_rich and self.console:
            with self.console.status(f"[cyan]{message}[/cyan]", spinner="dots"):
                result = await coro
                return result
        else:
            print(f"⏳ {message}...")
            result = await coro
            return result
    
    def _show_progress(self, total: int, description: str = "Processing"):
        """Create and return a progress context manager."""
        if self.has_rich and self.console:
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            )
        return None
    
    async def _confirm_action(self, message: str, default: bool = False) -> bool:
        """Ask for confirmation before action."""
        if self.has_rich and self.console:
            return Confirm.ask(f"[yellow]{message}[/yellow]", default=default)
        else:
            default_text = "Y/n" if default else "y/N"
            response = input(f"{message} ({default_text}): ").strip().lower()
            if not response:
                return default
            return response in ['y', 'yes']
    
    async def _show_menu(self, title: str, options: List[tuple], back_option: bool = True) -> Optional[str]:
        """Show beautiful interactive menu."""
        if self.has_prompt_toolkit:
            return await self._show_menu_prompt_toolkit(title, options, back_option)
        elif self.has_rich:
            return await asyncio.to_thread(self._show_menu_rich, title, options, back_option)
        else:
            return await asyncio.to_thread(self._show_menu_simple, title, options, back_option)
    
    async def _show_menu_prompt_toolkit(self, title: str, options: List[tuple], back_option: bool) -> Optional[str]:
        """Show beautiful menu using prompt_toolkit with custom menu - Enter to select immediately."""
        menu_options = options.copy()
        if back_option:
            menu_options.append(("back", "Back"))
        
        try:
            # Track selected index
            selected_index = [0]
            
            def get_formatted_text():
                """Generate formatted text with current selection."""
                from prompt_toolkit.formatted_text import FormattedText
                result = []
                for i, (value, label) in enumerate(menu_options):
                    if i == selected_index[0]:
                        # Selected item - highlighted with blue background
                        result.append(('bg:#2563EB #FFFFFF bold', f"  {label}  "))
                    else:
                        # Normal item
                        result.append(('fg:#E0E0E0', f"  {label}  "))
                    if i < len(menu_options) - 1:
                        result.append(('', '\n'))
                return FormattedText(result)
            
            # Create FormattedTextControl for menu
            menu_control = FormattedTextControl(
                get_formatted_text,
                focusable=True
            )
            
            # Create layout with centered menu
            body = HSplit([
                Window(height=2),
                Label(title, style="bold #9CA3AF"),
                Window(height=1),
                Window(menu_control, height=len(menu_options), align=Window.Align.CENTER),
                Window(height=2),
                Label("↑↓ Navigate  |  Enter Select  |  Esc Back  |  Ctrl+C Exit", style="dim #6B7280"),
                Window(height=1),
            ])
            
            # Create key bindings for navigation and selection
            kb = KeyBindings()
            
            @kb.add('up')
            def go_up(event):
                if selected_index[0] > 0:
                    selected_index[0] -= 1
                    # Invalidate to force redraw
                    event.app.invalidate()
            
            @kb.add('down')
            def go_down(event):
                if selected_index[0] < len(menu_options) - 1:
                    selected_index[0] += 1
                    # Invalidate to force redraw
                    event.app.invalidate()
            
            @kb.add('escape')
            def cancel(event):
                event.app.exit(result=None)
            
            @kb.add('enter')
            def select(event):
                # Immediately return the selected value - no OK button needed
                selected_value = menu_options[selected_index[0]][0]
                event.app.exit(result=selected_value)
            
            # Also handle ctrl+c
            @kb.add('c-c')
            def exit_app(event):
                event.app.exit(result=None)
            
            # Create application with full screen and custom style
            app = Application(
                layout=Layout(body, focused_element=menu_control),
                key_bindings=kb,
                style=Style.from_dict({
                    'label': 'fg:#9CA3AF',
                }),
                full_screen=True,  # Use full screen for clean display
            )
            
            result = await app.run_async()
            return result
        except KeyboardInterrupt:
            return None
        except Exception as e:
            logger.error(f"Error showing menu: {e}")
            return await asyncio.to_thread(self._show_menu_rich, title, options, back_option)
    
    def _show_menu_rich(self, title: str, options: List[tuple], back_option: bool) -> Optional[str]:
        """Show beautiful menu using rich."""
        if not self.console:
            return self._show_menu_simple(title, options, back_option)
        
        # Clear screen before showing menu
        self._clear_screen()
        
        # Create menu panel
        menu_items = []
        for i, (value, label) in enumerate(options, 1):
            menu_items.append(f"[cyan]{i}.[/cyan] {label}")
        
        if back_option:
            menu_items.append(f"[cyan]{len(options) + 1}.[/cyan] [dim]← Back[/dim]")
        
        menu_text = "\n".join(menu_items)
        
        menu_panel = Panel(
            Align.left(Text.from_markup(menu_text)),
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        self.console.print(menu_panel)
        
        while True:
            try:
                choice = Prompt.ask("\n[cyan]Select option[/cyan]", default="1")
                choice_num = int(choice)
                
                if back_option and choice_num == len(options) + 1:
                    return "back"
                elif 1 <= choice_num <= len(options):
                    return options[choice_num - 1][0]
                else:
                    self.console.print("[red]Invalid option. Please try again.[/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                return None
    
    def _show_menu_simple(self, title: str, options: List[tuple], back_option: bool) -> Optional[str]:
        """Show simple text menu."""
        print(f"\n{'═' * 60}")
        print(f"  {title}".center(60))
        print(f"{'═' * 60}\n")
        
        for i, (value, label) in enumerate(options, 1):
            print(f"  {i}. {label}")
        
        if back_option:
            print(f"  {len(options) + 1}. ← Back")
        
        print()
        
        while True:
            try:
                choice = input("Select option: ").strip()
                if not choice:
                    continue
                
                choice_num = int(choice)
                
                if back_option and choice_num == len(options) + 1:
                    return "back"
                elif 1 <= choice_num <= len(options):
                    return options[choice_num - 1][0]
                else:
                    print("Invalid option. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                return None
    
    async def _get_input(self, prompt_text: str, validator=None, password: bool = False, allow_cancel: bool = True) -> Optional[str]:
        """Get user input with optional validation and cancel option."""
        if self.has_prompt_toolkit:
            def get_input_sync():
                try:
                    # Add cancel hint to prompt
                    full_prompt = f"{prompt_text} (Ctrl+C to cancel)" if allow_cancel else prompt_text
                    
                    if password:
                        value = pt_prompt(full_prompt, is_password=True)
                    else:
                        value = pt_prompt(full_prompt)
                    
                    # Check for cancel command
                    if allow_cancel and (value.lower() in ['cancel', 'c', 'back', 'b']):
                        return None
                    
                    if validator:
                        is_valid, error_msg = validator(value)
                        if not is_valid:
                            if self.has_rich and self.console:
                                self.console.print(f"[red]{error_msg}[/red]")
                            else:
                                print(f"Error: {error_msg}")
                            return None
                    return value
                except KeyboardInterrupt:
                    return None
            
            while True:
                result = await asyncio.to_thread(get_input_sync)
                if result is not None:
                    return result
                # If None and allow_cancel, return None (user cancelled)
                if allow_cancel:
                    return None
                if validator:
                    continue
                return None
        elif self.has_rich and self.console:
            def get_input_sync():
                while True:
                    try:
                        # Add cancel hint to prompt
                        full_prompt = f"{prompt_text} (Ctrl+C or 'cancel' to cancel)" if allow_cancel else prompt_text
                        
                        if password:
                            value = Prompt.ask(full_prompt, password=True)
                        else:
                            value = Prompt.ask(full_prompt)
                        
                        # Check for cancel command
                        if allow_cancel and (value.lower() in ['cancel', 'c', 'back', 'b']):
                            return None
                        
                        if validator:
                            is_valid, error_msg = validator(value)
                            if not is_valid:
                                self.console.print(f"[red]{error_msg}[/red]")
                                continue
                        return value
                    except KeyboardInterrupt:
                        return None
            
            return await asyncio.to_thread(get_input_sync)
        else:
            def get_input_sync():
                while True:
                    try:
                        # Add cancel hint to prompt
                        full_prompt = f"{prompt_text} (Ctrl+C or 'cancel' to cancel): " if allow_cancel else f"{prompt_text}: "
                        
                        if password:
                            import getpass
                            value = getpass.getpass(full_prompt)
                        else:
                            value = input(full_prompt).strip()
                        
                        # Check for cancel command
                        if allow_cancel and (value.lower() in ['cancel', 'c', 'back', 'b']):
                            return None
                        
                        if validator:
                            is_valid, error_msg = validator(value)
                            if not is_valid:
                                print(f"Error: {error_msg}")
                                continue
                        return value
                    except KeyboardInterrupt:
                        return None
            
            return await asyncio.to_thread(get_input_sync)
    
    async def main_menu(self):
        """Show main menu."""
        while True:
            # Show account count in header
            async with self.active_clients_lock:
                account_count = len(self.active_clients)
            
            header_title = f"Telegram Panel"
            if account_count > 0:
                header_title += f" • {account_count} Account{'s' if account_count > 1 else ''}"
            
            self._print_header(header_title)
            
            options = [
                ("account_management", "Account Management"),
                ("individual", "Individual Operations"),
                ("bulk", "Bulk Operations"),
                ("monitor", "Monitor Mode"),
                ("stats", "Statistics & Report"),
                ("exit", "Exit")
            ]
            
            choice = await self._show_menu("Main Menu", options, back_option=False)
            
            if choice == "exit" or choice is None:
                if self.has_rich and self.console:
                    self.console.print("\n[cyan]Goodbye![/cyan]\n")
                else:
                    print("\nGoodbye!\n")
                break
            elif choice == "account_management":
                await self.account_management_menu()
            elif choice == "individual":
                await self.individual_menu()
            elif choice == "bulk":
                await self.bulk_menu()
            elif choice == "monitor":
                await self.monitor_menu()
            elif choice == "stats":
                await self.stats_menu()
    
    async def account_management_menu(self):
        """Account management menu."""
        while True:
            self._print_header("Account Management")
            
            options = [
                ("add", "Add Account"),
                ("list", "List Accounts"),
                ("inactive", "Inactive Accounts"),
                ("remove", "Remove Account"),
                ("back", "Back")
            ]
            
            choice = await self._show_menu("Account Management", options, back_option=False)
            
            if choice == "back" or choice is None:
                break
            elif choice == "add":
                await self.add_account_flow()
            elif choice == "list":
                await self.list_accounts_flow()
            elif choice == "inactive":
                await self.show_inactive_accounts_flow()
            elif choice == "remove":
                await self.remove_account_flow()
    
    async def add_account_flow(self):
        """Add account flow."""
        self._print_header("Add Account")
        
        phone = await self._get_input("Enter phone number (e.g., +1234567890)", 
                                     InputValidator.validate_phone_number,
                                     allow_cancel=True)
        if not phone:
            self._clear_screen()
            return
        
        try:
            session_name = sanitize_session_name(phone)
            
            if session_name in self.active_clients:
                self._print_error(f"Account {session_name} already exists")
                return
            
            # Show loading while connecting
            client = TelegramClient(session_name, API_ID, API_HASH)
            await self._show_loading("Connecting to Telegram", client.connect())
            
            if not await client.is_user_authorized():
                # Show loading while sending code
                await self._show_loading("Sending verification code", client.send_code_request(phone))
                self._print_success("Verification code sent! Check your Telegram app.", wait=False)
                
                code = await self._get_input("Enter verification code", allow_cancel=True)
                if not code:
                    await client.disconnect()
                    self._clear_screen()
                    return
                
                try:
                    await self._show_loading("Verifying code", client.sign_in(phone, code))
                except SessionPasswordNeededError:
                    password = await self._get_input("Enter 2FA password", password=True, allow_cancel=True)
                    if not password:
                        await client.disconnect()
                        self._clear_screen()
                        return
                    await self._show_loading("Verifying 2FA password", client.sign_in(password=password))
            
            async with self.active_clients_lock:
                self.active_clients[session_name] = client
            
            if 'clients' not in self.config:
                self.config['clients'] = {}
            self.config['clients'][session_name] = {
                'phone': phone,
                'enabled': True
            }
            self.config_manager.save_config(self.config)
            
            self._print_success(f"Account {session_name} added successfully")
            
        except Exception as e:
            logger.error(f"Error adding account: {e}")
            self._print_error(str(e))
    
    async def list_accounts_flow(self):
        """List accounts flow."""
        self._print_header("Account List")
        
        async with self.active_clients_lock:
            accounts = list(self.active_clients.keys())
        
        if not accounts:
            self._print_info("No accounts available")
            input("\nPress Enter to continue...")
            return
        
        if self.has_rich and self.console:
            table = Table(title="Available Accounts", box=box.ROUNDED, border_style="cyan")
            table.add_column("#", style="cyan", width=5, justify="center")
            table.add_column("Session Name", style="green")
            
            for i, acc in enumerate(accounts, 1):
                table.add_row(str(i), acc)
            
            self.console.print(table)
        else:
            print("\nAvailable Accounts:")
            for i, acc in enumerate(accounts, 1):
                print(f"  {i}. {acc}")
        
        input("\nPress Enter to continue...")
    
    async def remove_account_flow(self):
        """Remove account flow."""
        self._print_header("Remove Account")
        
        async with self.active_clients_lock:
            accounts = list(self.active_clients.keys())
        
        if not accounts:
            self._print_info("No accounts available")
            return
        
        options = [(acc, acc) for acc in accounts]
        choice = await self._show_menu("Select Account to Remove", options)
        
        if choice and choice != "back":
            if self.has_rich and self.console:
                confirm_remove = Confirm.ask(f"Are you sure you want to remove [cyan]{choice}[/cyan]?")
            else:
                confirm_remove = input(f"Are you sure you want to remove {choice}? (yes/no): ").lower() == 'yes'
            
            if confirm_remove:
                async with self.active_clients_lock:
                    if choice in self.active_clients:
                        client = self.active_clients[choice]
                        if client.is_connected():
                            await client.disconnect()
                        del self.active_clients[choice]
                
                if choice in self.config.get('clients', {}):
                    del self.config['clients'][choice]
                    self.config_manager.save_config(self.config)
                
                self._print_success(f"Account {choice} removed successfully")
    
    async def individual_menu(self):
        """Individual operations menu."""
        async with self.active_clients_lock:
            accounts = list(self.active_clients.keys())
        
        if not accounts:
            self._clear_screen()
            self._print_info("No accounts available")
            input("\nPress Enter to continue...")
            return
        
        while True:
            self._print_header("Individual Operations")
            
            options = [
                ("reaction", "Reaction"),
                ("vote", "Vote in Poll"),
                ("join", "Join Group/Channel"),
                ("leave", "Leave Group/Channel"),
                ("block", "Block User"),
                ("send_pv", "Send Private Message"),
                ("comment", "Post Comment"),
                ("back", "Back")
            ]
            
            choice = await self._show_menu("Individual Operations", options, back_option=False)
            
            if choice == "back" or choice is None:
                break
            
            # Select account
            account_options = [(acc, acc) for acc in accounts]
            account_choice = await self._show_menu("Select Account", account_options)
            
            if account_choice and account_choice != "back":
                if choice == "reaction":
                    await self.individual_reaction(account_choice)
                elif choice == "vote":
                    await self.individual_vote(account_choice)
                elif choice == "join":
                    await self.individual_join(account_choice)
                elif choice == "leave":
                    await self.individual_leave(account_choice)
                elif choice == "block":
                    await self.individual_block(account_choice)
                elif choice == "send_pv":
                    await self.individual_send_pv(account_choice)
                elif choice == "comment":
                    await self.individual_comment(account_choice)
    
    async def individual_reaction(self, session_name: str):
        """Individual reaction operation."""
        self._print_header("Apply Reaction")
        
        link = await self._get_input("Enter message link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        reactions = [
            ("👍", "Thumbs Up"),
            ("❤️", "Heart"),
            ("😂", "Laugh"),
            ("😮", "Wow"),
            ("😢", "Sad"),
            ("😡", "Angry")
        ]
        
        reaction_choice = await self._show_menu("Select Reaction", reactions)
        if reaction_choice and reaction_choice != "back":
            async with self.active_clients_lock:
                account = self.active_clients.get(session_name)
            
            if account:
                try:
                    if not account.is_connected():
                        await self._show_loading("Connecting account", account.connect())
                    await self._show_loading(f"Applying reaction {reaction_choice}", 
                                            self.actions.apply_reaction(account, link, reaction_choice))
                    self._print_success(f"Reaction {reaction_choice} applied successfully")
                except Exception as e:
                    self._print_error(str(e))
    
    async def individual_vote(self, session_name: str):
        """Individual vote operation."""
        self._print_header("Vote in Poll")
        
        link = await self._get_input("Enter poll link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        option_str = await self._get_input("Enter option number (1-10)", 
                                          lambda x: InputValidator.validate_poll_option(x),
                                          allow_cancel=True)
        if not option_str:
            self._clear_screen()
            return
        
        _, _, option_num = InputValidator.validate_poll_option(option_str)
        option = option_num - 1
        
        async with self.active_clients_lock:
            account = self.active_clients.get(session_name)
        
        if account:
            try:
                if not account.is_connected():
                    await account.connect()
                
                chat_entity, message_id = await self.actions.parse_telegram_link(link, account)
                if chat_entity is None or message_id is None:
                    self._print_error("Failed to parse link")
                    return
                
                from src.utils import resolve_entity
                from telethon.tl.functions.messages import SendVoteRequest
                chat_entity = await resolve_entity(chat_entity, account)
                
                message = await account.get_messages(chat_entity, ids=message_id)
                if not message.poll:
                    self._print_error("The provided link does not point to a poll")
                    return
                
                await account(SendVoteRequest(
                    peer=chat_entity,
                    msg_id=message_id,
                    options=[bytes([option])]
                ))
                
                self._print_success(f"Voted for option {option_num} successfully")
            except Exception as e:
                self._print_error(str(e))
    
    async def individual_join(self, session_name: str):
        """Individual join operation."""
        self._print_header("Join Group/Channel")
        
        link = await self._get_input("Enter group/channel link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            account = self.active_clients.get(session_name)
        
        if account:
            try:
                if not account.is_connected():
                    await account.connect()
                
                if hasattr(account, 'join_chat'):
                    await account.join_chat(link)
                else:
                    from src.utils import resolve_entity
                    from telethon.tl.functions.channels import JoinChannelRequest
                    entity = await resolve_entity(link, account)
                    await account(JoinChannelRequest(entity))
                
                self._print_success(f"Successfully joined {link}")
            except Exception as e:
                self._print_error(str(e))
    
    async def individual_leave(self, session_name: str):
        """Individual leave operation."""
        self._print_header("Leave Group/Channel")
        
        link = await self._get_input("Enter group/channel link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            account = self.active_clients.get(session_name)
        
        if account:
            try:
                if not account.is_connected():
                    await account.connect()
                
                from src.utils import resolve_entity
                entity = await account.get_entity(link)
                await account.leave_chat(entity)
                
                self._print_success(f"Successfully left {link}")
            except Exception as e:
                self._print_error(str(e))
    
    async def individual_block(self, session_name: str):
        """Individual block operation."""
        self._print_header("Block User")
        
        user_input = await self._get_input("Enter username or user ID", allow_cancel=True)
        if not user_input:
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            account = self.active_clients.get(session_name)
        
        if account:
            try:
                if not account.is_connected():
                    await account.connect()
                
                from src.utils import resolve_entity
                from telethon.tl.functions.contacts import BlockRequest
                entity = await resolve_entity(user_input, account)
                await account(BlockRequest(entity))
                
                self._print_success(f"User {user_input} blocked successfully")
            except Exception as e:
                self._print_error(str(e))
    
    async def individual_send_pv(self, session_name: str):
        """Individual send PV operation."""
        self._print_header("Send Private Message")
        
        user_input = await self._get_input("Enter username or user ID", allow_cancel=True)
        if not user_input:
            self._clear_screen()
            return
        
        message = await self._get_input("Enter message text", InputValidator.validate_message_text, allow_cancel=True)
        if not message:
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            account = self.active_clients.get(session_name)
        
        if account:
            try:
                if not account.is_connected():
                    await account.connect()
                
                from src.utils import resolve_entity
                entity = await resolve_entity(user_input, account)
                await account.send_message(entity, message)
                
                self._print_success(f"Message sent successfully to {user_input}")
            except Exception as e:
                self._print_error(str(e))
    
    async def individual_comment(self, session_name: str):
        """Individual comment operation."""
        self._print_header("Post Comment")
        
        link = await self._get_input("Enter message link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        comment_text = await self._get_input("Enter comment text", InputValidator.validate_message_text, allow_cancel=True)
        if not comment_text:
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            account = self.active_clients.get(session_name)
        
        if account:
            try:
                if not account.is_connected():
                    await account.connect()
                
                chat_entity, message_id = await self.actions.parse_telegram_link(link, account)
                if chat_entity is None or message_id is None:
                    self._print_error("Failed to parse link")
                    return
                
                from src.utils import resolve_entity
                chat_entity = await resolve_entity(chat_entity, account)
                await account.send_message(chat_entity, comment_text, reply_to=message_id)
                
                self._print_success("Comment sent successfully")
            except Exception as e:
                self._print_error(str(e))
    
    async def bulk_menu(self):
        """Bulk operations menu."""
        async with self.active_clients_lock:
            num_accounts = len(self.active_clients)
        
        if num_accounts == 0:
            self._clear_screen()
            self._print_info("No accounts available")
            input("\nPress Enter to continue...")
            return
        
        while True:
            self._print_header("Bulk Operations")
            
            options = [
                ("reaction", "Bulk Reaction"),
                ("vote", "Bulk Vote"),
                ("join", "Bulk Join"),
                ("leave", "Bulk Leave"),
                ("block", "Bulk Block"),
                ("send_pv", "Bulk Send PV"),
                ("comment", "Bulk Comment"),
                ("back", "Back")
            ]
            
            choice = await self._show_menu("Bulk Operations", options, back_option=False)
            
            if choice == "back" or choice is None:
                break
            
            # Get number of accounts
            num_str = await self._get_input(f"Enter number of accounts (1-{num_accounts})", allow_cancel=True)
            if not num_str:
                self._clear_screen()
                continue
            
            try:
                num = int(num_str)
                if num < 1 or num > num_accounts:
                    self._print_error(f"Number must be between 1 and {num_accounts}")
                    continue
            except ValueError:
                self._print_error("Invalid number")
                continue
            
            if choice == "reaction":
                await self.bulk_reaction(num)
            elif choice == "vote":
                await self.bulk_vote(num)
            elif choice == "join":
                await self.bulk_join(num)
            elif choice == "leave":
                await self.bulk_leave(num)
            elif choice == "block":
                await self.bulk_block(num)
            elif choice == "send_pv":
                await self.bulk_send_pv(num)
            elif choice == "comment":
                await self.bulk_comment(num)
    
    async def bulk_reaction(self, num_accounts: int):
        """Bulk reaction operation."""
        self._print_header("Bulk Reaction")
        
        link = await self._get_input("Enter message link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        reactions = [
            ("👍", "Thumbs Up"),
            ("❤️", "Heart"),
            ("😂", "Laugh"),
            ("😮", "Wow"),
            ("😢", "Sad"),
            ("😡", "Angry")
        ]
        
        reaction_choice = await self._show_menu("Select Reaction", reactions)
        if reaction_choice and reaction_choice != "back":
            await self._execute_bulk_operation('reaction', num_accounts, link=link, reaction=reaction_choice)
    
    async def bulk_vote(self, num_accounts: int):
        """Bulk vote operation."""
        self._print_header("Bulk Vote")
        
        link = await self._get_input("Enter poll link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        option_str = await self._get_input("Enter option number (1-10)", 
                                          lambda x: InputValidator.validate_poll_option(x),
                                          allow_cancel=True)
        if not option_str:
            self._clear_screen()
            return
        
        _, _, option_num = InputValidator.validate_poll_option(option_str)
        await self._execute_bulk_operation('vote', num_accounts, link=link, option=option_num)
    
    async def bulk_join(self, num_accounts: int):
        """Bulk join operation."""
        self._print_header("Bulk Join")
        
        link = await self._get_input("Enter group/channel link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        await self._execute_bulk_operation('join', num_accounts, link=link)
    
    async def bulk_leave(self, num_accounts: int):
        """Bulk leave operation."""
        self._print_header("Bulk Leave")
        
        link = await self._get_input("Enter group/channel link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        await self._execute_bulk_operation('leave', num_accounts, link=link)
    
    async def bulk_block(self, num_accounts: int):
        """Bulk block operation."""
        self._print_header("Bulk Block")
        
        user_input = await self._get_input("Enter username or user ID", allow_cancel=True)
        if not user_input:
            self._clear_screen()
            return
        
        await self._execute_bulk_operation('block', num_accounts, user_input=user_input)
    
    async def bulk_send_pv(self, num_accounts: int):
        """Bulk send PV operation."""
        self._print_header("Bulk Send PV")
        
        user_input = await self._get_input("Enter username or user ID", allow_cancel=True)
        if not user_input:
            self._clear_screen()
            return
        
        message = await self._get_input("Enter message text", InputValidator.validate_message_text, allow_cancel=True)
        if not message:
            self._clear_screen()
            return
        
        await self._execute_bulk_operation('send_pv', num_accounts, user_input=user_input, message=message)
    
    async def bulk_comment(self, num_accounts: int):
        """Bulk comment operation."""
        self._print_header("Bulk Comment")
        
        link = await self._get_input("Enter message link", InputValidator.validate_telegram_link, allow_cancel=True)
        if not link:
            self._clear_screen()
            return
        
        comment_text = await self._get_input("Enter comment text", InputValidator.validate_message_text, allow_cancel=True)
        if not comment_text:
            self._clear_screen()
            return
        
        await self._execute_bulk_operation('comment', num_accounts, link=link, comment_text=comment_text)
    
    async def _execute_bulk_operation(self, operation: str, num_accounts: int, **kwargs):
        """Execute bulk operation."""
        async with self.active_clients_lock:
            accounts = list(self.active_clients.values())[:num_accounts]
        
        if not accounts:
            self._print_info("No accounts available")
            return
        
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
            self._print_info("No connected accounts available")
            return
        
        success_count = 0
        error_count = 0
        
        self._print_info(f"Executing {operation} with {len(valid_accounts)} accounts...")
        
        if self.has_rich and self.console:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
                TimeRemainingColumn(),
                console=self.console,
                transient=False
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Executing {operation}...[/cyan]", 
                    total=len(valid_accounts)
                )
                
                for account in valid_accounts:
                    try:
                        session_name = get_session_name(account)
                        progress.update(task, description=f"Processing {session_name}...")
                        
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
                        progress.update(task, advance=1, description=f"[green]✓[/green] {session_name} completed")
                        
                    except Exception as e:
                        error_count += 1
                        progress.update(task, advance=1, description=f"[red]✗[/red] {get_session_name(account)} failed")
                        logger.error(f"Error in bulk operation for {get_session_name(account)}: {e}")
        else:
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
                    print(f"✗ {get_session_name(account)}: {str(e)}")
        
        # Show summary with better formatting
        self._clear_screen()
        if self.has_rich and self.console:
            summary_table = Table(title="Operation Summary", box=box.ROUNDED, border_style="cyan")
            summary_table.add_column("Status", style="cyan", width=15)
            summary_table.add_column("Count", style="green", justify="right")
            
            if success_count > 0:
                summary_table.add_row("[bold green]✓ Success[/bold green]", str(success_count))
            if error_count > 0:
                summary_table.add_row("[bold red]✗ Errors[/bold red]", str(error_count))
            
            self.console.print(summary_table)
            input("\nPress Enter to continue...")
            self._clear_screen()
        else:
            result_msg = f"Operation completed: {success_count} success, {error_count} errors"
            if success_count > 0:
                self._print_success(result_msg, wait=True)
            elif error_count > 0:
                self._print_error(result_msg, wait=True)
            else:
                self._print_info(result_msg, wait=True)
    
    async def monitor_menu(self):
        """Monitor mode menu."""
        while True:
            self._print_header("Monitor Mode")
            
            # Show current status
            keywords_count = len(self.config.get('KEYWORDS', []))
            ignored_users_count = len(self.config.get('IGNORE_USERS', []))
            
            if self.has_rich and self.console:
                status_table = Table(title="Monitor Status", box=box.ROUNDED, border_style="cyan", show_header=False)
                status_table.add_column("Metric", style="cyan")
                status_table.add_column("Value", style="green")
                status_table.add_row("Keywords", str(keywords_count))
                status_table.add_row("Ignored Users", str(ignored_users_count))
                self.console.print(status_table)
                self.console.print()
            else:
                print(f"Keywords: {keywords_count}")
                print(f"Ignored Users: {ignored_users_count}\n")
            
            options = [
                ("add_keyword", "Add Keyword"),
                ("remove_keyword", "Remove Keyword"),
                ("ignore_user", "Ignore User"),
                ("remove_ignore", "Remove Ignore User"),
                ("update_groups", "Update Groups"),
                ("show_groups", "Show Groups"),
                ("show_keywords", "Show Keywords"),
                ("show_ignores", "Show Ignored Users"),
                ("back", "Back")
            ]
            
            choice = await self._show_menu("Monitor Mode", options, back_option=False)
            
            if choice == "back" or choice is None:
                break
            elif choice == "add_keyword":
                await self.add_keyword_flow()
            elif choice == "remove_keyword":
                await self.remove_keyword_flow()
            elif choice == "ignore_user":
                await self.ignore_user_flow()
            elif choice == "remove_ignore":
                await self.remove_ignore_user_flow()
            elif choice == "update_groups":
                await self.update_groups_flow()
            elif choice == "show_groups":
                await self.show_groups_flow()
            elif choice == "show_keywords":
                await self.show_keywords_flow()
            elif choice == "show_ignores":
                await self.show_ignores_flow()
    
    async def add_keyword_flow(self):
        """Add keyword flow."""
        self._print_header("Add Keyword")
        
        keyword = await self._get_input("Enter keyword to monitor", 
                                       InputValidator.validate_keyword,
                                       allow_cancel=True)
        if not keyword:
            self._clear_screen()
            return
        
        if 'KEYWORDS' not in self.config:
            self.config['KEYWORDS'] = []
        
        if keyword in self.config['KEYWORDS']:
            self._print_error(f"Keyword '{keyword}' already exists")
        else:
            self.config['KEYWORDS'].append(keyword)
            self.config_manager.save_config(self.config)
            self._print_success(f"Keyword '{keyword}' added successfully")
            
            # Show current keywords
            keywords = ', '.join(self.config['KEYWORDS'])
            self._print_info(f"Current keywords: {keywords}")
    
    async def remove_keyword_flow(self):
        """Remove keyword flow."""
        self._print_header("Remove Keyword")
        
        if not self.config.get('KEYWORDS'):
            self._print_info("No keywords configured")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        # Show current keywords
        keywords = self.config['KEYWORDS']
        if self.has_rich and self.console:
            keywords_table = Table(title="Current Keywords", box=box.ROUNDED, border_style="cyan")
            keywords_table.add_column("#", style="cyan", width=5, justify="center")
            keywords_table.add_column("Keyword", style="green")
            
            for i, kw in enumerate(keywords, 1):
                keywords_table.add_row(str(i), kw)
            
            self.console.print(keywords_table)
            self.console.print()
        else:
            print("\nCurrent Keywords:")
            for i, kw in enumerate(keywords, 1):
                print(f"  {i}. {kw}")
            print()
        
        keyword = await self._get_input("Enter keyword to remove", allow_cancel=True)
        if not keyword:
            self._clear_screen()
            return
        
        if keyword in self.config['KEYWORDS']:
            self.config['KEYWORDS'].remove(keyword)
            self.config_manager.save_config(self.config)
            self._print_success(f"Keyword '{keyword}' removed successfully")
            
            # Show updated keywords
            remaining = ', '.join(self.config['KEYWORDS']) if self.config['KEYWORDS'] else "None"
            self._print_info(f"Current keywords: {remaining}")
        else:
            self._print_error(f"Keyword '{keyword}' not found")
    
    async def ignore_user_flow(self):
        """Ignore user flow."""
        self._print_header("Ignore User")
        
        user_input = await self._get_input("Enter user ID to ignore", allow_cancel=True)
        if not user_input:
            self._clear_screen()
            return
        
        # Validate user ID
        is_valid, error_msg, user_id = InputValidator.validate_user_id(user_input.strip())
        if not is_valid:
            self._print_error(error_msg)
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        if 'IGNORE_USERS' not in self.config:
            self.config['IGNORE_USERS'] = []
        
        if user_id in self.config['IGNORE_USERS']:
            self._print_error(f"User ID {user_id} is already ignored")
        else:
            self.config['IGNORE_USERS'].append(user_id)
            self.config_manager.save_config(self.config)
            self._print_success(f"User ID {user_id} is now ignored")
            
            # Show ignored users
            ignored = ', '.join(str(u) for u in self.config['IGNORE_USERS'])
            self._print_info(f"Ignored users: {ignored}")
    
    async def remove_ignore_user_flow(self):
        """Remove ignore user flow."""
        self._print_header("Remove Ignore User")
        
        if not self.config.get('IGNORE_USERS'):
            self._print_info("No users are currently ignored")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        # Show current ignored users
        ignored_users = self.config['IGNORE_USERS']
        if self.has_rich and self.console:
            ignores_table = Table(title="Ignored Users", box=box.ROUNDED, border_style="cyan")
            ignores_table.add_column("#", style="cyan", width=5, justify="center")
            ignores_table.add_column("User ID", style="green")
            
            for i, uid in enumerate(ignored_users, 1):
                ignores_table.add_row(str(i), str(uid))
            
            self.console.print(ignores_table)
            self.console.print()
        else:
            print("\nIgnored Users:")
            for i, uid in enumerate(ignored_users, 1):
                print(f"  {i}. User ID: {uid}")
            print()
        
        user_input = await self._get_input("Enter user ID to remove from ignore list", allow_cancel=True)
        if not user_input:
            self._clear_screen()
            return
        
        # Validate user ID
        is_valid, error_msg, user_id = InputValidator.validate_user_id(user_input.strip())
        if not is_valid:
            self._print_error(error_msg)
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        if user_id in self.config['IGNORE_USERS']:
            self.config['IGNORE_USERS'].remove(user_id)
            self.config_manager.save_config(self.config)
            self._print_success(f"User ID {user_id} is no longer ignored")
            
            # Show updated ignored users
            remaining = ', '.join(str(u) for u in self.config['IGNORE_USERS']) if self.config['IGNORE_USERS'] else "None"
            self._print_info(f"Ignored users: {remaining}")
        else:
            self._print_error(f"User ID {user_id} not found in ignored list")
    
    async def update_groups_flow(self):
        """Update groups flow."""
        self._print_header("Update Groups")
        
        async with self.active_clients_lock:
            accounts = list(self.active_clients.items())
        
        if not accounts:
            self._print_error("No accounts available")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        self._print_info(f"Updating groups for {len(accounts)} account(s)...")
        
        if self.has_rich and self.console:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
                TimeRemainingColumn(),
                console=self.console,
                transient=False
            ) as progress:
                task = progress.add_task(
                    "[cyan]Updating groups...[/cyan]",
                    total=len(accounts)
                )
                
                groups_per_client = {}
                for session_name, client in accounts:
                    try:
                        progress.update(task, description=f"[cyan]Processing {session_name}...[/cyan]")
                        
                        from telethon.tl.types import Chat, Channel
                        group_ids = set()
                        
                        async for dialog in client.iter_dialogs(limit=5000):
                            try:
                                if isinstance(dialog.entity, (Chat, Channel)) and not (
                                    isinstance(dialog.entity, Channel) and dialog.entity.broadcast
                                ):
                                    group_ids.add(dialog.entity.id)
                            except Exception as e:
                                logger.error(f"Error processing dialog for {session_name}: {e}")
                                continue
                        
                        groups_per_client[session_name] = list(group_ids)
                        progress.update(task, advance=1, description=f"[green]✓[/green] {session_name}: {len(group_ids)} groups")
                        
                    except Exception as e:
                        logger.error(f"Error updating groups for {session_name}: {e}")
                        progress.update(task, advance=1, description=f"[red]✗[/red] {session_name} failed")
                
                # Save to config
                if 'clients' not in self.config:
                    self.config['clients'] = {}
                
                for session_name, groups in groups_per_client.items():
                    if session_name not in self.config['clients']:
                        self.config['clients'][session_name] = {}
                    self.config['clients'][session_name] = groups
                
                self.config_manager.save_config(self.config)
                
                total_groups = sum(len(groups) for groups in groups_per_client.values())
                progress.update(task, description=f"[green]✓ Complete: {total_groups} total groups[/green]")
        else:
            groups_per_client = {}
            for session_name, client in accounts:
                try:
                    print(f"Processing {session_name}...")
                    
                    from telethon.tl.types import Chat, Channel
                    group_ids = set()
                    
                    async for dialog in client.iter_dialogs(limit=5000):
                        try:
                            if isinstance(dialog.entity, (Chat, Channel)) and not (
                                isinstance(dialog.entity, Channel) and dialog.entity.broadcast
                            ):
                                group_ids.add(dialog.entity.id)
                        except Exception as e:
                            logger.error(f"Error processing dialog for {session_name}: {e}")
                            continue
                    
                    groups_per_client[session_name] = list(group_ids)
                    print(f"✓ {session_name}: {len(group_ids)} groups")
                    
                except Exception as e:
                    logger.error(f"Error updating groups for {session_name}: {e}")
                    print(f"✗ {session_name}: Error")
            
            # Save to config
            if 'clients' not in self.config:
                self.config['clients'] = {}
            
            for session_name, groups in groups_per_client.items():
                if session_name not in self.config['clients']:
                    self.config['clients'][session_name] = {}
                self.config['clients'][session_name] = groups
            
            self.config_manager.save_config(self.config)
            
            total_groups = sum(len(groups) for groups in groups_per_client.values())
            print(f"\n✓ Complete: {total_groups} total groups")
        
        self._print_success("Groups updated successfully")
    
    async def show_groups_flow(self):
        """Show groups flow."""
        self._print_header("Groups per Account")
        
        clients_data = self.config.get('clients', {})
        
        if not isinstance(clients_data, dict) or not clients_data:
            self._print_info("No groups found. Please run 'Update Groups' first.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            active_sessions = set(self.active_clients.keys())
        
        if self.has_rich and self.console:
            groups_table = Table(title="Groups per Account", box=box.ROUNDED, border_style="cyan")
            groups_table.add_column("Account", style="cyan")
            groups_table.add_column("Groups Count", style="green", justify="right")
            
            total_groups = 0
            for session, groups in clients_data.items():
                # Skip revoked sessions
                if session not in active_sessions:
                    if 'inactive_accounts' not in self.config or session not in self.config['inactive_accounts']:
                        continue
                    else:
                        inactive_reason = self.config['inactive_accounts'][session].get('reason', '').lower()
                        if 'revoked' in inactive_reason or 'auth' in inactive_reason or 'session' in inactive_reason:
                            continue
                
                phone = session.replace('.session', '') if session else 'Unknown'
                groups_count = len(groups) if isinstance(groups, list) else 0
                total_groups += groups_count
                groups_table.add_row(phone, str(groups_count))
            
            groups_table.add_row("[bold]Total[/bold]", f"[bold]{total_groups}[/bold]", style="bold")
            self.console.print(groups_table)
        else:
            print("\nGroups per Account:\n")
            total_groups = 0
            for session, groups in clients_data.items():
                # Skip revoked sessions
                if session not in active_sessions:
                    if 'inactive_accounts' not in self.config or session not in self.config['inactive_accounts']:
                        continue
                    else:
                        inactive_reason = self.config['inactive_accounts'][session].get('reason', '').lower()
                        if 'revoked' in inactive_reason or 'auth' in inactive_reason or 'session' in inactive_reason:
                            continue
                
                phone = session.replace('.session', '') if session else 'Unknown'
                groups_count = len(groups) if isinstance(groups, list) else 0
                total_groups += groups_count
                print(f"  • {phone}: {groups_count} groups")
            
            print(f"\nTotal: {total_groups} groups")
        
        input("\nPress Enter to continue...")
        self._clear_screen()
    
    async def show_keywords_flow(self):
        """Show keywords flow."""
        self._print_header("Configured Keywords")
        
        keywords = self.config.get('KEYWORDS', [])
        
        if not keywords:
            self._print_info("No keywords configured yet.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        if self.has_rich and self.console:
            keywords_table = Table(title="Configured Keywords", box=box.ROUNDED, border_style="cyan")
            keywords_table.add_column("#", style="cyan", width=5, justify="center")
            keywords_table.add_column("Keyword", style="green")
            
            for idx, keyword in enumerate(keywords, 1):
                keywords_table.add_row(str(idx), keyword)
            
            self.console.print(keywords_table)
        else:
            print("\nConfigured Keywords:\n")
            for idx, keyword in enumerate(keywords, 1):
                print(f"  {idx}. {keyword}")
        
        input("\nPress Enter to continue...")
        self._clear_screen()
    
    async def show_ignores_flow(self):
        """Show ignored users flow."""
        self._print_header("Ignored Users")
        
        ignored_users = self.config.get('IGNORE_USERS', [])
        
        if not ignored_users:
            self._print_info("No users are currently ignored.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        if self.has_rich and self.console:
            ignores_table = Table(title="Ignored Users", box=box.ROUNDED, border_style="cyan")
            ignores_table.add_column("#", style="cyan", width=5, justify="center")
            ignores_table.add_column("User ID", style="green")
            
            for idx, user_id in enumerate(ignored_users, 1):
                ignores_table.add_row(str(idx), str(user_id))
            
            self.console.print(ignores_table)
        else:
            print("\nIgnored Users:\n")
            for idx, user_id in enumerate(ignored_users, 1):
                print(f"  {idx}. User ID: {user_id}")
        
        input("\nPress Enter to continue...")
        self._clear_screen()
    
    async def stats_menu(self):
        """Statistics menu."""
        while True:
            self._print_header("Statistics & Report")
            
            options = [
                ("show_stats", "Show Statistics"),
                ("check_report", "Check Report Status"),
                ("back", "Back")
            ]
            
            choice = await self._show_menu("Statistics & Report", options, back_option=False)
            
            if choice == "back" or choice is None:
                break
            elif choice == "show_stats":
                await self.show_stats_flow()
            elif choice == "check_report":
                await self.check_report_status_flow()
    
    async def show_stats_flow(self):
        """Show statistics flow."""
        self._print_header("Bot Statistics")
        
        async with self.active_clients_lock:
            num_accounts = len(self.active_clients)
        
        total_accounts = len(self.config.get('clients', {}))
        keywords_count = len(self.config.get('KEYWORDS', []))
        ignored_users_count = len(self.config.get('IGNORE_USERS', []))
        inactive_count = len(self.config.get('inactive_accounts', {}))
        
        if self.has_rich and self.console:
            stats_table = Table(title="Bot Statistics", box=box.ROUNDED, border_style="cyan")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="green")
            
            stats_table.add_row("Total Accounts", str(total_accounts))
            stats_table.add_row("Active Accounts", str(num_accounts))
            stats_table.add_row("Inactive Accounts", str(inactive_count))
            stats_table.add_row("Keywords", str(keywords_count))
            stats_table.add_row("Ignored Users", str(ignored_users_count))
            
            self.console.print(stats_table)
        else:
            print(f"\nStatistics:")
            print(f"  Total Accounts: {total_accounts}")
            print(f"  Active Accounts: {num_accounts}")
            print(f"  Inactive Accounts: {inactive_count}")
            print(f"  Keywords: {keywords_count}")
            print(f"  Ignored Users: {ignored_users_count}")
        
        input("\nPress Enter to continue...")
        self._clear_screen()
    
    async def show_inactive_accounts_flow(self):
        """Show inactive accounts flow."""
        self._print_header("Inactive Accounts")
        
        if 'inactive_accounts' not in self.config:
            self.config['inactive_accounts'] = {}
        
        inactive_accounts = self.config.get('inactive_accounts', {})
        
        if not inactive_accounts:
            self._print_info("No inactive accounts found. All accounts are working properly.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        if self.has_rich and self.console:
            inactive_table = Table(title=f"Inactive Accounts ({len(inactive_accounts)})", box=box.ROUNDED, border_style="cyan")
            inactive_table.add_column("Phone", style="cyan")
            inactive_table.add_column("Reason", style="yellow")
            inactive_table.add_column("Last Seen", style="dim")
            
            import time
            for phone, account_info in inactive_accounts.items():
                reason = account_info.get('reason', 'unknown')
                last_seen = account_info.get('last_seen', 0)
                
                try:
                    last_seen_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_seen))
                except (ValueError, OSError):
                    last_seen_str = 'Unknown'
                
                inactive_table.add_row(phone, reason, last_seen_str)
            
            self.console.print(inactive_table)
        else:
            print(f"\nInactive Accounts ({len(inactive_accounts)}):\n")
            import time
            for phone, account_info in inactive_accounts.items():
                reason = account_info.get('reason', 'unknown')
                last_seen = account_info.get('last_seen', 0)
                error_details = account_info.get('error_details', 'No details available')
                
                try:
                    last_seen_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_seen))
                except (ValueError, OSError):
                    last_seen_str = 'Unknown'
                
                print(f"  Phone: {phone}")
                print(f"    Reason: {reason}")
                print(f"    Last seen: {last_seen_str}")
                print(f"    Error: {error_details[:100]}{'...' if len(error_details) > 100 else ''}\n")
        
        input("\nPress Enter to continue...")
        self._clear_screen()
    
    async def check_report_status_flow(self):
        """Check report status flow."""
        self._print_header("Check Report Status")
        
        from src.Config import REPORT_CHECK_BOT
        if not REPORT_CHECK_BOT:
            self._print_error("REPORT_CHECK_BOT not configured. Please set it in .env file.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        clients_data = self.config.get('clients', {})
        if not clients_data:
            self._print_info("No accounts found to check.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        async with self.active_clients_lock:
            active_sessions = set(self.active_clients.keys())
            sessions_to_check = [s for s in clients_data.keys() if s in active_sessions]
        
        if not sessions_to_check:
            self._print_info("No active accounts to check.")
            input("\nPress Enter to continue...")
            self._clear_screen()
            return
        
        self._print_info(f"Checking report status for {len(sessions_to_check)} account(s)... This may take a while.")
        
        reported_accounts = []
        checked_count = 0
        
        if self.has_rich and self.console:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
                TimeRemainingColumn(),
                console=self.console,
                transient=False
            ) as progress:
                task = progress.add_task(
                    "[cyan]Checking report status...[/cyan]",
                    total=len(sessions_to_check)
                )
                
                for session_name in sessions_to_check:
                    try:
                        phone_number = session_name.replace('.session', '').strip()
                        if not phone_number.startswith('+'):
                            phone_number = '+' + phone_number
                        
                        async with self.active_clients_lock:
                            account = self.active_clients.get(session_name)
                        
                        if account:
                            checked_count += 1
                            progress.update(task, description=f"[cyan]Checking {phone_number}...[/cyan]")
                            
                            is_reported = await self.actions.check_report_status(phone_number, account)
                            
                            if is_reported:
                                reported_accounts.append(session_name)
                                progress.update(task, advance=1, description=f"[red]✗[/red] {phone_number} is reported")
                            else:
                                progress.update(task, advance=1, description=f"[green]✓[/green] {phone_number} OK")
                    except Exception as e:
                        logger.error(f"Error checking report status for {session_name}: {e}")
                        progress.update(task, advance=1, description=f"[yellow]⚠[/yellow] {session_name} error")
        else:
            for session_name in sessions_to_check:
                try:
                    phone_number = session_name.replace('.session', '').strip()
                    if not phone_number.startswith('+'):
                        phone_number = '+' + phone_number
                    
                    async with self.active_clients_lock:
                        account = self.active_clients.get(session_name)
                    
                    if account:
                        checked_count += 1
                        print(f"Checking {phone_number}...")
                        
                        is_reported = await self.actions.check_report_status(phone_number, account)
                        
                        if is_reported:
                            reported_accounts.append(session_name)
                            print(f"✗ {phone_number} is reported")
                        else:
                            print(f"✓ {phone_number} OK")
                except Exception as e:
                    logger.error(f"Error checking report status for {session_name}: {e}")
                    print(f"⚠ {session_name}: Error")
        
        # Show results
        self._clear_screen()
        if self.has_rich and self.console:
            result_table = Table(title="Report Status Results", box=box.ROUNDED, border_style="cyan")
            result_table.add_column("Status", style="cyan", width=15)
            result_table.add_column("Count", style="green", justify="right")
            
            result_table.add_row("[bold green]✓ Checked[/bold green]", str(checked_count))
            if reported_accounts:
                result_table.add_row("[bold red]✗ Reported[/bold red]", str(len(reported_accounts)))
            
            self.console.print(result_table)
            
            if reported_accounts:
                self.console.print("\n[bold red]Reported Accounts:[/bold red]")
                for acc in reported_accounts:
                    phone = acc.replace('.session', '')
                    self.console.print(f"  • {phone}")
        else:
            print(f"\nReport Status Results:")
            print(f"  Checked: {checked_count}")
            if reported_accounts:
                print(f"  Reported: {len(reported_accounts)}")
                print("\nReported Accounts:")
                for acc in reported_accounts:
                    phone = acc.replace('.session', '')
                    print(f"  • {phone}")
        
        input("\nPress Enter to continue...")
        self._clear_screen()
    
    async def cleanup(self):
        """Cleanup and disconnect all clients."""
        async with self.active_clients_lock:
            for client in self.active_clients.values():
                try:
                    if client.is_connected():
                        await client.disconnect()
                except Exception:
                    pass
    
    async def run(self):
        """Run interactive CLI."""
        try:
            await self.initialize()
            await self.main_menu()
        except KeyboardInterrupt:
            if self.has_rich and self.console:
                self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
            else:
                print("\nOperation cancelled by user")
        except Exception as e:
            logger.error(f"Interactive CLI error: {e}", exc_info=True)
            self._print_error(str(e))
        finally:
            await self.cleanup()


def main():
    """Main entry point for interactive CLI."""
    setup_logging()
    cli = InteractiveCLI()
    asyncio.run(cli.run())


if __name__ == '__main__':
    main()
