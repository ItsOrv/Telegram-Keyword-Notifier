from telethon import events
from handlers.account_handler import AccountHandler
from handlers.keyword_handler import KeywordHandler
from handlers.stats_handler import StatsHandler
import logging

logger = logging.getLogger(__name__)

class CallbackHandler:
    def __init__(self, bot):
        self.bot = bot

    async def callback_handler(self, event):
        """Handle callback queries"""
        logger.info("callback_handler in CallbackHandler")
        try:
            data = event.data.decode()

            if data == 'add_account':
                logger.info("add_account in callback_handler in CallbackHandler")
                await AccountHandler(self.bot).add_account(event)
            elif data == 'request_phone_number':
                logger.info("request_phone_number in callback_handler in CallbackHandler")
                await event.respond("Please enter your phone number:")
                self.bot._conversations[event.chat_id] = 'phone_number_handler'
            elif data == 'show_accounts':
                logger.info("show_accounts in callback_handler in CallbackHandler")
                await AccountHandler(self.bot).show_accounts(event)
            elif data == 'update_groups':
                logger.info("update_groups in callback_handler in CallbackHandler")
                await AccountHandler(self.bot).update_groups(event)
            elif data.startswith('toggle_'):
                logger.info("toggle_ in callback_handler in CallbackHandler")
                session = data.replace('toggle_', '')
                await AccountHandler(self.bot).toggle_client(session, event)
            elif data.startswith('delete_'):
                logger.info("delete_ in callback_handler in CallbackHandler")
                session = data.replace('delete_', '')
                await AccountHandler(self.bot).delete_client(session, event)
            elif data == 'add_keyword':
                logger.info("add_keyword in callback_handler in CallbackHandler")
                await KeywordHandler(self.bot).add_keyword_handler(event)
            elif data == 'remove_keyword':
                logger.info("remove_keyword in callback_handler in CallbackHandler")
                await KeywordHandler(self.bot).remove_keyword_handler(event)
            elif data == 'show_stats':
                logger.info("show_stats in callback_handler in CallbackHandler")
                await StatsHandler(self.bot).show_stats(event)
            
        except Exception as e:
            logger.error(f"Error in callback_handler: {e}")
            await event.respond("Error processing request. Please try again.")
