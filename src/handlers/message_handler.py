from telethon import events

class MessageHandler:
    def __init__(self, bot):
        self.bot = bot

    async def message_handler(self, event):
        """Handle incoming messages based on conversation state"""
        if event.chat_id in self.bot._conversations:
            handler_name = self.bot._conversations[event.chat_id]
            if handler_name in self.bot.handlers:
                await self.bot.handlers[handler_name](event)
                del self.bot._conversations[event.chat_id]
                return True
        return False
