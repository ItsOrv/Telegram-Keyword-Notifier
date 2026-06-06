import logging
from telethon import Button
from telethon.errors import MessageIdInvalidError

logger = logging.getLogger(__name__)

# Header text shown above each named keyboard.
KEYBOARD_MESSAGES = {
    'start': "🤖 Telegram Management Bot\n\nPlease select an option:",
    'monitor': "📡 Monitor Mode\n\nPlease select an option:",
    'bulk': "⚡ Bulk Operations\n\nPlease select an operation:",
    'account_management': "👤 Account Management\n\nPlease select an option:",
    'individual_keyboard': "🎯 Individual Operations\n\nPlease select an operation:",
    'report': "📊 Report Status\n\nPlease select an option:",
}

class Keyboard:
    """
    Provides static methods for generating inline keyboard layouts.

    All methods return lists of button rows that can be used with
    Telethon's Button.inline() for creating interactive keyboards.
    """

    @staticmethod
    async def edit_or_respond(event, text, buttons=None):
        """
        Update the message in place when possible, otherwise send a new one.

        Editing the existing message (instead of sending a new one) keeps the
        chat clean: navigating between menus, prompting for input, and
        cancelling all reuse a single message rather than stacking stale menus.
        """
        if event is None:
            return
        try:
            if hasattr(event, 'answer'):
                await event.answer()
        except Exception:
            pass
        try:
            await event.edit(text, buttons=buttons)
        except MessageIdInvalidError:
            # Original message can't be edited (e.g. it was a plain user message)
            await event.respond(text, buttons=buttons)
        except Exception as e:
            logger.debug(f"edit failed ({e}); sending a new message instead")
            await event.respond(text, buttons=buttons)

    @staticmethod
    def start_keyboard():
        """
        Generate the main start menu keyboard.

        Returns:
            List of button rows for the main menu
        """
        return [
            [Button.inline("👤 Account Management", 'account_management')],
            [
                Button.inline("🎯 Individual", 'individual_keyboard'),
                Button.inline("⚡ Bulk", 'bulk_operations')
            ],
            [Button.inline("📡 Monitor Mode", 'monitor_mode')],
            [Button.inline("📊 Report Status", 'report')]
        ]

    @staticmethod
    def monitor_keyboard():
        """
        Generate the monitor mode keyboard.

        Returns:
            List of button rows for monitor operations
        """
        return [
            [
                Button.inline('➕ Add Keyword', 'add_keyword'),
                Button.inline('➖ Remove Keyword', 'remove_keyword')
            ],
            [
                Button.inline('🔇 Ignore User', 'ignore_user'),
                Button.inline('🔊 Remove Ignore', 'remove_ignore_user')
            ],
            [Button.inline("🔄 Update Groups", 'update_groups')],
            [
                Button.inline('📁 Show Groups', 'show_groups'),
                Button.inline('🏷 Show Keywords', 'show_keyword')
            ],
            [Button.inline("🚫 Show Ignores", 'show_ignores')],
            [Button.inline("🔙 Back", 'back_to_start')]
        ]

    @staticmethod
    def bulk_keyboard():
        """
        Generate the bulk operations keyboard.

        Returns:
            List of button rows for bulk operations
        """
        return [
            [
                Button.inline('👍 Reaction', 'bulk_reaction'),
                Button.inline('📊 Poll', 'bulk_poll')
            ],
            [
                Button.inline('➕ Join', 'bulk_join'),
                Button.inline('🚪 Leave', 'bulk_leave')
            ],
            [
                Button.inline('🚫 Block', 'bulk_block'),
                Button.inline('✉️ Send PV', 'bulk_send_pv')
            ],
            [Button.inline('💬 Comment', 'bulk_comment')],
            [Button.inline("🔙 Back", 'back_to_start')]
        ]

    @staticmethod
    def account_management_keyboard(tbot=None, chat_id=None):
        """
        Generate the account management keyboard.

        Dynamically adjusts buttons based on current conversation state.

        Args:
            tbot: Optional TelegramBot instance
            chat_id: Optional chat ID to check conversation state

        Returns:
            List of button rows for account management
        """
        buttons = [
            [Button.inline('➕ Add Account', 'add_account')],
            [Button.inline('📋 List Accounts', 'list_accounts')],
            [Button.inline('💤 Inactive Accounts', 'inactive_accounts')],
            [Button.inline("🔙 Back", 'back_to_start')]
        ]

        if tbot and chat_id and chat_id in tbot._conversations:
            conversation_state = tbot._conversations[chat_id]
            if conversation_state.startswith('bulk_send_pv') or conversation_state.startswith('bulk_poll'):
                buttons.pop(1)

        return buttons

    @staticmethod
    def channel_message_keyboard(message_link: str, sender_id: int):
        """
        Generate keyboard for forwarded messages in channel.

        Args:
            message_link: URL to the original message
            sender_id: ID of the message sender

        Returns:
            List of button rows with view and ignore options
        """
        return [
            [Button.url("🔗 View Message", url=message_link)],
            [Button.inline("🔇 Ignore", data=f"ignore_{sender_id}")]
        ]

    @staticmethod
    def toggle_and_delete_keyboard(status: str, session: str):
        """
        Generate keyboard for account management actions.

        Args:
            status: Current account status (e.g., "🟢 Active")
            session: Session name/identifier

        Returns:
            List of button rows with toggle and delete options
        """
        # Exact match: "Active" is a substring of "Inactive", so a loose `in`
        # check would label inactive accounts "Disable".
        is_active = status.strip() == "Active"
        return [
            [
                Button.inline(
                    "⛔ Disable" if is_active else "✅ Enable",
                    data=f"toggle_{session}"
                ),
                Button.inline("🗑 Delete", data=f"delete_{session}")
            ]
        ]

    @staticmethod
    def individual_keyboard():
        """
        Generate the individual operations keyboard.

        Returns:
            List of button rows for individual account operations
        """
        return [
            [
                Button.inline("👍 Reaction", 'reaction'),
                Button.inline("✉️ Send PV", 'send_pv')
            ],
            [
                Button.inline("➕ Join", 'join'),
                Button.inline("🚪 Leave", 'left')
            ],
            [
                Button.inline("🚫 Block", 'block'),
                Button.inline("💬 Comment", 'comment')
            ],
            [Button.inline("🔙 Back", 'back_to_start')]
        ]

    @staticmethod
    def report_keyboard():
        """
        Generate the report/statistics keyboard.

        Returns:
            List of button rows for report operations
        """
        return [
            [Button.inline("📈 Show Stats", 'show_stats')],
            [Button.inline("🛡 Check Report Status", 'check_report_status')],
            [Button.inline("🔙 Back", 'back_to_start')]
        ]

    @staticmethod
    def add_back_button(buttons, back_action='back_to_start'):
        """
        Add a back button to a keyboard layout.

        Args:
            buttons: List of button rows
            back_action: Callback data for the back button

        Returns:
            List of button rows with back button added
        """
        if not isinstance(buttons, list):
            return buttons

        # Create a copy to avoid modifying the original
        result = [row[:] for row in buttons]

        # Add back button as a new row
        result.append([Button.inline("🔙 Back", back_action)])

        return result

    @staticmethod
    def add_cancel_button(buttons):
        """
        Add a cancel button to a keyboard layout.

        Args:
            buttons: List of button rows

        Returns:
            List of button rows with cancel button added
        """
        if not isinstance(buttons, list):
            return buttons

        # Create a copy to avoid modifying the original
        result = [row[:] for row in buttons]

        # Add cancel button as a new row
        result.append([Button.inline("❌ Cancel", 'cancel')])

        return result

    @staticmethod
    async def show_keyboard(keyboard_name: str, event=None, tbot=None):
        """
        Display a keyboard by name.

        Dynamically selects and displays the appropriate keyboard layout
        based on the keyboard name. Handles both callback queries and
        new messages.

        Args:
            keyboard_name: Name of the keyboard to display
            event: Optional Telegram event (CallbackQuery or NewMessage)
            tbot: Optional TelegramBot instance for dynamic keyboards

        Returns:
            Keyboard layout (list of button rows) or None if not found
        """
        chat_id = event.chat_id if event else None

        keyboards = {
            'start': Keyboard.start_keyboard(),
            'monitor': Keyboard.monitor_keyboard(),
            'bulk': Keyboard.bulk_keyboard(),
            'account_management': Keyboard.account_management_keyboard(tbot, chat_id),
            'channel_message': Keyboard.channel_message_keyboard,
            'toggle_and_delete': Keyboard.toggle_and_delete_keyboard,
            'individual_keyboard': Keyboard.individual_keyboard(),
            'report': Keyboard.report_keyboard()
        }

        # Return the keyboard if it exists
        keyboard = keyboards.get(keyboard_name, None)

        if keyboard is None:
            logger.warning(f"Keyboard {keyboard_name} not found")
            if event:
                await event.respond("Sorry, the requested keyboard is not available.")
            return None

        # Handle function references (channel_message, toggle_and_delete)
        if callable(keyboard):
            logger.warning(f"Keyboard {keyboard_name} is a function reference, not a keyboard layout")
            if event:
                await event.respond("Sorry, this keyboard requires additional parameters.")
            return None

        # Validate keyboard format / non-empty
        if not isinstance(keyboard, list) or len(keyboard) == 0:
            logger.error(f"Invalid or empty keyboard for {keyboard_name}: {type(keyboard)}")
            if event:
                await event.respond("Sorry, the requested keyboard is not available.")
            return None

        if event:
            message_text = KEYBOARD_MESSAGES.get(keyboard_name, "Please select an option:")
            # Edit in place (falls back to a new message) so navigation reuses
            # one message instead of leaving stale menus behind.
            await Keyboard.edit_or_respond(event, message_text, buttons=keyboard)
        return keyboard
