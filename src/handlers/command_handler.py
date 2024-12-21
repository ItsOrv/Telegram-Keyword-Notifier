from telethon import events, Button
from asyncio.log import logger

class CommandHandler:
    def __init__(self, bot):
        self.bot = bot

    async def start_command(self, event):
        """Handle /start command"""
        try:
            buttons = [
                [Button.inline("➕ Add Account", b'add_account')],
                [Button.inline("👥 Show Accounts", b'show_accounts')],
                [Button.inline("🔄 Update Groups", b'update_groups')],
                [
                    Button.inline('🔑 Add Keyword', b'add_keyword'),
                    Button.inline('❌ Remove Keyword', b'remove_keyword')
                ],
                [
                    Button.inline('🚫 Ignore User', b'ignore_user'),
                    Button.inline('✅ Remove Ignore', b'remove_ignore_user')
                ],
                [Button.inline('📊 Stats', b'show_stats')]
            ]

            await event.respond(
                "🤖 Welcome to Telegram Management Bot\n\n"
                "Choose an option from the menu below:",
                buttons=buttons
            )

        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await event.respond("Error showing menu. Please try again.")
