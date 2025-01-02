import os
import json
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SESSION_NAME = os.getenv('SESSION_NAME')

"""
CONFIG_FILE = 'clients.json'

def load_json_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def update_json_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

json_config = load_json_config()
"""