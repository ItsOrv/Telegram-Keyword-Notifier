import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(name, default=None):
    value = os.getenv(name)
    if not value and default is None:
        raise ValueError(f"{name} environment variable not set.")
    return value

API_ID = int(get_env_variable('API_ID'))
API_HASH = get_env_variable('API_HASH')
BOT_TOKEN = get_env_variable('BOT_TOKEN')

TARGET_GROUPS = [int(group_id.strip()) for group_id in get_env_variable('TARGET_GROUPS', '').split(',') if group_id.strip()]

KEYWORDS = [keyword.strip() for keyword in get_env_variable('KEYWORDS', '').split(',') if keyword.strip()]

CHANNEL_ID = os.getenv('CHANNEL_ID')
SESSION_NAME = get_env_variable('SESSION_NAME')

IGNORE_USERS = [int(user_id.strip()) for user_id in get_env_variable('IGNORE_USERS', '').split(',') if user_id.strip()]
