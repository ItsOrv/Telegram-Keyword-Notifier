import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Setup logging configuration
def setup_logging(log_filename: str = "bot.log") -> None:
    """Sets up basic logging configuration with path security"""
    # Sanitize log filename to prevent path traversal
    import re
    log_filename = re.sub(r'[^\w\-_\.]', '', log_filename)
    if not log_filename.endswith('.log'):
        log_filename = "bot.log"
    
    log_path = os.path.join(LOG_DIR, log_filename)
    # Ensure the resolved path is still within LOG_DIR
    if not os.path.abspath(log_path).startswith(os.path.abspath(LOG_DIR)):
        log_path = os.path.join(LOG_DIR, "bot.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )