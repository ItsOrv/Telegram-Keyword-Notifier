import os
import json
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SESSION_NAME = os.getenv('SESSION_NAME')

