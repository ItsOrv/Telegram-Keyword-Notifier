import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUPS = list(map(int, os.getenv('TARGET_GROUPS').split(',')))
KEYWORDS = os.getenv('KEYWORDS').split(',')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SESSION_NAME = os.getenv('SESSION_NAME')
