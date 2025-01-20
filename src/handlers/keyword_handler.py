from telethon import events
import logging

logger = logging.getLogger(__name__)

class KeywordHandler:
    def __init__(self, bot):
        self.bot = bot

    async def add_keyword_handler(self, event):
        """Add a keyword to monitor"""
        logger.info("add_keyword_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the keyword you want to add.")
                self.bot._conversations[event.chat_id] = 'add_keyword_handler'
                return

            keyword = str(event.message.text.strip())
            if keyword not in self.bot.config['KEYWORDS']:
                self.bot.config['KEYWORDS'].append(keyword)
                self.bot.config_manager.save_config(self.bot.config)  # ذخیره و ادغام تنظیمات جدید با تنظیمات موجود
                await event.respond(f"✅ Keyword '{keyword}' added successfully")
            else:
                await event.respond(f"⚠️ Keyword '{keyword}' already exists")

            keywords = ', '.join(str(k) for k in self.bot.config['KEYWORDS'])  # تبدیل همه به رشته
            await event.respond(f"📝 Current keywords: {keywords}")

        except Exception as e:
            logger.error(f"Error adding keyword: {e}")
            await event.respond("❌ Error adding keyword")

    async def remove_keyword_handler(self, event):
        """Remove a keyword from monitoring"""
        logger.info("remove_keyword_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the keyword you want to remove.")
                self.bot._conversations[event.chat_id] = 'remove_keyword_handler'
                return

            keyword = str(event.message.text.strip())  # تبدیل به رشته
            if keyword in self.bot.config['KEYWORDS']:
                self.bot.config['KEYWORDS'].remove(keyword)
                self.bot.config_manager.save_config(self.bot.config)  # ذخیره و ادغام تنظیمات جدید با تنظیمات موجود
                await event.respond(f"✅ Keyword '{keyword}' removed successfully")
            else:
                await event.respond(f"⚠️ Keyword '{keyword}' not found")

            keywords = ', '.join(str(k) for k in self.bot.config['KEYWORDS'])  # تبدیل همه به رشته
            await event.respond(f"📝 Current keywords: {keywords}")

        except Exception as e:
            logger.error(f"Error removing keyword: {e}")
            await event.respond("❌ Error removing keyword")

    async def ignore_user_handler(self, event):
        """Ignore a user from further interaction"""
        logger.info("ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the user ID you want to ignore.")
                self.bot._conversations[event.chat_id] = 'ignore_user_handler'
                return

            user_id = int(event.message.text.strip())  # تبدیل به عدد صحیح
            if user_id not in self.bot.config['IGNORE_USERS']:
                self.bot.config['IGNORE_USERS'].append(user_id)  # بدون تبدیل به رشته
                self.bot.config_manager.save_config(self.bot.config)  # ذخیره و ادغام تنظیمات جدید با تنظیمات موجود
                await event.respond(f"✅ User ID {user_id} is now ignored")
            else:
                await event.respond(f"⚠️ User ID {user_id} is already ignored")

            ignored_users = ', '.join(str(u) for u in self.bot.config['IGNORE_USERS'])  # تبدیل به رشته برای نمایش
            await event.respond(f"📝 Ignored users: {ignored_users}")

        except Exception as e:
            logger.error(f"Error ignoring user: {e}")
            await event.respond("❌ Error ignoring user")

    async def delete_ignore_user_handler(self, event):
        """Remove a user from the ignore list"""
        logger.info("delete_ignore_user_handler in KeywordHandler")
        try:
            if isinstance(event, events.CallbackQuery.Event):
                await event.respond("Please enter the user ID you want to stop ignoring.")
                self.bot._conversations[event.chat_id] = 'delete_ignore_user_handler'
                return

            user_id = int(event.message.text.strip())  # تبدیل به عدد صحیح
            if user_id in self.bot.config['IGNORE_USERS']:
                self.bot.config['IGNORE_USERS'].remove(user_id)  # بدون تبدیل به رشته
                self.bot.config_manager.save_config(self.bot.config)  # ذخیره و ادغام تنظیمات جدید با تنظیمات موجود
                await event.respond(f"✅ User ID {user_id} is no longer ignored")
            else:
                await event.respond(f"⚠️ User ID {user_id} not found in ignored list")

            ignored_users = ', '.join(str(u) for u in self.bot.config['IGNORE_USERS'])  # تبدیل به رشته برای نمایش
            await event.respond(f"📝 Ignored users: {ignored_users}")

        except Exception as e:
            logger.error(f"Error deleting ignored user: {e}")
            await event.respond("❌ Error deleting ignored user")
