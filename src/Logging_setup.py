import logging
import os
from asyncio.log import logger


# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Setup logging configuration
def setup_logging(log_filename="bot.log"):
    logger.info("setup_logging in logging_setup")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, log_filename)),
            logging.StreamHandler()
        ]
    )
