from telethon import events, Button
import logging
from handlers.account_handler import AccountHandler

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, bot):
        self.bot = bot

    async def start_command(self, event):
        """Handle /start command"""
        logger.info("start command in CommandHandler")
        try:
            buttons = [
                [Button.inline("Add Account", 'add_account')],
                [Button.inline("Show Accounts", b'show_accounts')],
                [Button.inline("Update Groups", b'update_groups')],
                [
                    Button.inline('Add Keyword', b'add_keyword'),
                    Button.inline('Remove Keyword', b'remove_keyword')
                ],
                [
                    Button.inline('Ignore User', b'ignore_user'),
                    Button.inline('Remove Ignore', b'remove_ignore_user')
                ],
                [Button.inline('Stats', b'show_stats')]
                ]

            await event.respond(
                "Telegram Management Bot\n\n",
                buttons=buttons
            )

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await event.respond("Error showing menu. Please try again.")
