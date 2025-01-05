import logging
from telethon import events

logger = logging.getLogger(__name__)

class StatsHandler:
    def __init__(self, bot):
        self.bot = bot

    async def show_stats(self, event):
        """Show bot statistics"""
        logger.info("show_stats in StatsHandler")
        try:
            stats = {
                "Total Accounts": len(self.bot.config['clients']),
                "Active Accounts": len(self.bot.active_clients),
                "Keywords": len(self.bot.config['KEYWORDS']),
                "Ignored Users": len(self.bot.config['IGNORE_USERS'])
            }

            text = "📊 Bot Statistics\n\n"
            for key, value in stats.items():
                text += f"• {key}: {value}\n"

            await event.respond(text)

        except Exception as e:
            logger.error(f"Error showing stats: {e}")
            await event.respond("❌ Error showing statistics")
