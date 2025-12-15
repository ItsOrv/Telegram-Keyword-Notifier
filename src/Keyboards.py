import logging
from telethon import Button

logger = logging.getLogger(__name__)

class Keyboard:

    @staticmethod
    def start_keyboard():
        """Returns the start menu keyboard"""
        return [
            [Button.inline("Account Management", 'account_management')],
            [
                Button.inline("Individual", 'individual_keyboard'),
                Button.inline("Bulk", 'bulk_operations')
            ],
            [Button.inline("Monitor Mode", 'monitor_mode')],
            [Button.inline("Report", 'report')]
        ]

    @staticmethod
    def monitor_keyboard():
        """Returns the monitor mode keyboard"""
        return [
            [
                Button.inline('Add Keyword', b'add_keyword'),
                Button.inline('Remove Keyword', b'remove_keyword')
            ],
            [
                Button.inline('Ignore User', b'ignore_user'),
                Button.inline('Remove Ignore', b'remove_ignore_user')
            ],
            [Button.inline("Update Groups", b'update_groups')],
            [
                Button.inline('Show Groups', b'show_groups'),
                Button.inline('Show Keyword', b'show_keyword')
            ],
            [Button.inline("Show Ignores", b'show_ignores')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def bulk_keyboard():
        """Returns a keyboard with action buttons like like, join, block, message, comment"""
        return [
            [Button.inline('Reaction', 'bulk_reaction')],
            [Button.inline('Poll', 'bulk_poll')],
            [Button.inline('Join', 'bulk_join')],
            [Button.inline('Block', 'bulk_block')],
            [Button.inline('Send pv', 'bulk_send_pv')],
            [Button.inline('Comment', 'bulk_comment')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def account_management_keyboard():
        """Returns the keyboard for account management"""
        return [
            [Button.inline('Add Account', 'add_account')],
            [Button.inline('List Accounts', 'list_accounts')],
            [Button.inline('Inactive Accounts', 'inactive_accounts')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def channel_message_keyboard(message_link, sender_id):
        """Returns a keyboard with a 'View Message' URL button and 'Ignore' inline button"""
        return [
            [Button.url("View Message", url=message_link)],
            [Button.inline("❌Ignore❌", data=f"ignore_{sender_id}")]
        ]

    @staticmethod
    def toggle_and_delete_keyboard(status, session):
        """Returns a keyboard with 'Disable/Enable' and 'Delete' buttons"""
        return [
            [
                Button.inline(
                    "❌ Disable" if status == "🟢 Active" else "✅ Enable",
                    data=f"toggle_{session}"
                ),
                Button.inline("🗑 Delete", data=f"delete_{session}")
            ]
        ]

    @staticmethod
    def individual_keyboard():
        """Returns the keyboard for individual operations"""
        return [
            [Button.inline("Reaction", 'reaction')],
            [Button.inline("Send PV", 'send_pv')],
            [Button.inline("Join", 'join')],
            [Button.inline("Left", 'left')],
            [Button.inline("Comment", 'comment')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    def report_keyboard():
        """Returns the keyboard for report"""
        return [
            [Button.inline("Show Stats", 'show_stats')],
            [Button.inline("Exit", 'exit')]
        ]

    @staticmethod
    async def show_keyboard(keyboard_name, event=None):
        """Dynamically returns and shows the requested keyboard based on its name"""
        keyboards = {
            'start': Keyboard.start_keyboard(),
            'monitor': Keyboard.monitor_keyboard(),
            'bulk': Keyboard.bulk_keyboard(),
            'account_management': Keyboard.account_management_keyboard(),
            'channel_message': Keyboard.channel_message_keyboard,
            'toggle_and_delete': Keyboard.toggle_and_delete_keyboard,
            'individual_keyboard': Keyboard.individual_keyboard(),
            'report': Keyboard.report_keyboard()
        }

        # Return the keyboard if it exists
        keyboard = keyboards.get(keyboard_name, None)

        if keyboard:
            if event:
                try:
                    # For callback queries, answer first and then edit
                    if hasattr(event, 'answer'):
                        await event.answer()
                    # Clear the previous keyboard
                    await event.edit("Please choose an option:", buttons=keyboard)
                except Exception as e:
                    logger.error(f"Error showing keyboard {keyboard_name}: {e}")
                    # If edit fails, try responding
                    await event.respond("Please choose an option:", buttons=keyboard)
            return keyboard
        else:
            if event:
                await event.respond("Sorry, the requested keyboard is not available.")
            return None

