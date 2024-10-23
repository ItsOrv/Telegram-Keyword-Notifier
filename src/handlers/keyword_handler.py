from telethon import events

class KeywordHandler:
    def __init__(self, bot):
        self.bot = bot

    async def add_keyword_handler(self, event):
        """Add a keyword to monitor"""
        try:
            keyword = event.message.text.strip()
            if keyword not in self.bot.config['KEYWORDS']:
                self.bot.config['KEYWORDS'].append(keyword)
                self.bot.config_manager.save_config()
                await event.respond(f"✅ Keyword '{keyword}' added successfully")
            else:
                await event.respond(f"⚠️ Keyword '{keyword}' already exists")

            # Show current keywords
            keywords = ', '.join(self.bot.config['KEYWORDS'])
            await event.respond(f"📝 Current keywords: {keywords}")

        except Exception as e:
            logger.error(f"Error adding keyword: {e}")
            await event.respond("❌ Error adding keyword")

    async def remove_keyword_handler(self, event):
        """Remove a keyword from monitoring"""
        try:
            keyword = event.message.text.strip()
            if keyword in self.bot.config['KEYWORDS']:
                self.bot.config['KEYWORDS'].remove(keyword)
                self.bot.config_manager.save_config()
                await event.respond(f"✅ Keyword '{keyword}' removed successfully")
            else:
                await event.respond(f"⚠️ Keyword '{keyword}' not found")

            # Show remaining keywords
            keywords = ', '.join(self.bot.config['KEYWORDS'])
            await event.respond(f"📝 Current keywords: {keywords}")

        except Exception as e:
            logger.error(f"Error removing keyword: {e}")
            await event.respond("❌ Error removing keyword")
