import asyncio
import logging
import os
from pathlib import Path
from src.Telbot import TelegramBot
from src.Logger import setup_logging

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
    # Ensure we're in the correct directory for .env file
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    setup_logging()
    main()
