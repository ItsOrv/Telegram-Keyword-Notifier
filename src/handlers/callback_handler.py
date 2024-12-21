from telethon import events
from handlers.account_handler import AccountHandler
from asyncio.log import logger

class CallbackHandler:
    def __init__(self, bot):
        self.bot = bot

    async def callback_handler(self, event):
        """Handle callback queries"""
        try:
            data = event.data.decode()

            if data == 'add_account':
                await AccountHandler(self.bot).add_account(event)
            elif data == 'show_accounts':
                await AccountHandler(self.bot).show_accounts(event)
            elif data == 'update_groups':
                await AccountHandler(self.bot).update_groups(event)
            elif data.startswith('toggle_'):
                session = data.replace('toggle_', '')
                await AccountHandler(self.bot).toggle_client(session, event)
            elif data.startswith('delete_'):
                session = data.replace('delete_', '')
                await AccountHandler(self.bot).delete_client(session, event)
            # Add other callback handlers here

        except Exception as e:
            logger.error(f"Error in callback_handler: {e}")
            await event.respond("Error processing request. Please try again.")
