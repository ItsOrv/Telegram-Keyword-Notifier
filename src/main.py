import asyncio
import logging
from bot import TelegramBot
from utils.logging_setup import setup_logging

def main():
    try:
        bot = TelegramBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.critical(f"Critical error in main: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    setup_logging()
    main()
