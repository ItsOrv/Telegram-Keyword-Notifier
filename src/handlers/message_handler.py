from telethon import events
from handlers.account_handler import AccountHandler
from handlers.keyword_handler import KeywordHandler
import logging
from asyncio.log import logger

class MessageHandler:
    def __init__(self, bot):
        self.bot = bot
        self.account_handler = AccountHandler(bot)
        self.keyword_handler = KeywordHandler(bot)


    async def message_handler(self, event):
        """Handle incoming messages based on conversation state"""
        logger.info("message_handler in MessageHandler")
        
        if event.chat_id in self.bot._conversations:
            handler_name = self.bot._conversations[event.chat_id]
            
            if handler_name == 'phone_number_handler':
                await self.account_handler.phone_number_handler(event)
                return True

            elif handler_name == 'code_handler':
                await self.account_handler.code_handler(event)
                return True

            elif handler_name == 'password_handler':
                await self.account_handler.password_handler(event)
                return True

            elif handler_name == 'ignore_user_handler':
                await self.keyword_handler.ignore_user_handler(event)
                return True

            elif handler_name == 'delete_ignore_user_handler':
                await self.keyword_handler.delete_ignore_user_handler(event)
                return True

            elif handler_name == 'add_keyword_handler':
                await self.keyword_handler.add_keyword_handler(event)
                return True

            elif handler_name == 'remove_keyword_handler':
                await self.keyword_handler.remove_keyword_handler(event)
                return True

        return False
