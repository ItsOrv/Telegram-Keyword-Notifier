import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load values from .env
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SESSION_NAME = os.getenv('SESSION_NAME')

# Load configuration from config.json
CONFIG_FILE = 'src/config.json'

def load_json_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def update_json_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Load dynamic config from JSON
json_config = load_json_config()

TARGET_GROUPS = json_config.get('TARGET_GROUPS', [])
KEYWORDS = json_config.get('KEYWORDS', [])
IGNORE_USERS = json_config.get('IGNORE_USERS', [])
