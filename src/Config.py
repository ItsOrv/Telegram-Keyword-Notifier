import os
import json
from dotenv import load_dotenv
import logging
from typing import Dict, Any, Union, Optional

# Set up logger for the configuration manager
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ConfigManager:
    def __init__(self, filename: str = "config.json", config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ConfigManager class.
        Handles loading, saving, and managing configuration settings.
        :param filename: Path to the configuration file.
        :param config: Initial configuration dictionary (optional).
        """
        try:
            # Store full path for file operations
            self.filepath = filename
            # Sanitize filename for display purposes only
            import re
            sanitized = re.sub(r'[^\w\-_\.]', '', os.path.basename(filename))
            if not sanitized.endswith('.json'):
                sanitized = "config.json"
            self.filename = sanitized
            self.default_config = {
                "TARGET_GROUPS": [],  # List of target groups for the bot
                "KEYWORDS": [],       # List of keywords for filtering
                "IGNORE_USERS": [],   # List of user IDs to ignore
                "clients": {}         # Dictionary of client configurations
            }
            # Load existing configuration or use the provided one
            self.config = config if config else self.load_config()  # type: Dict[str, Any]
            logger.info("ConfigManager initialized successfully.")
        except Exception as e:
            logger.critical(f"Error initializing ConfigManager: {e}")
            raise

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from a JSON file.
        If the file doesn't exist or is invalid, the default configuration is used.
        :return: Configuration dictionary.
        """
        try:
            if not os.path.exists(self.filepath):
                logger.warning(f"Config file '{self.filepath}' not found. Using default settings.")
                return self.default_config.copy()
            
            if os.path.getsize(self.filepath) == 0:
                logger.warning(f"Config file '{self.filepath}' is empty. Using default settings.")
                return self.default_config.copy()

            with open(self.filepath, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                if not isinstance(loaded_config, dict):
                    raise ValueError("Config file must contain a JSON object.")
                logger.info("Config file loaded successfully.")
                # Merge loaded configuration with default values
                return {**self.default_config, **loaded_config}
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.error(f"Error loading config file '{self.filepath}': {e}. Falling back to default config.")
            return self.default_config.copy()

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save the current configuration to the JSON file.
        :param config: Configuration dictionary to save.
        """
        try:
            # Update self.config to match the saved config
            self.config = config.copy()
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.filepath) if os.path.dirname(self.filepath) else '.', exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("Configuration saved successfully.")
        except OSError as e:
            logger.error(f"Failed to save config file '{self.filepath}': {e}")

    def update_config(self, key: str, value: Any) -> None:
        """
        Update a specific key in the configuration and save changes.
        :param key: Configuration key to update.
        :param value: New value for the key.
        """
        try:
            if key not in self.default_config:
                logger.warning(f"Key '{key}' not in default configuration. Adding it.")
            self.config[key] = value
            self.save_config(self.config)
        except Exception as e:
            logger.error(f"Error updating config key '{key}': {e}")

    def merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge a new configuration dictionary with the current configuration.
        :param new_config: Dictionary containing configuration updates.
        """
        try:
            # Reload current config from file to ensure we have the latest
            current_config = self.load_config()
            for key, value in new_config.items():
                if key in current_config and isinstance(current_config[key], list) and isinstance(value, list):
                    # Combine lists while avoiding duplicates but preserving all unique items
                    combined = current_config[key] + value
                    # Remove duplicates while preserving order
                    seen = set()
                    result = []
                    for item in combined:
                        if item not in seen:
                            seen.add(item)
                            result.append(item)
                    self.config[key] = result
                else:
                    self.config[key] = value
            self.save_config(self.config)
        except Exception as e:
            logger.error(f"Error merging config: {e}")

    def get_config(self, key: Optional[str] = None) -> Union[Dict[str, Any], Any]:
        """
        Retrieve a specific configuration value or the entire configuration.
        :param key: Configuration key to retrieve (optional).
        :return: Configuration value or the full configuration dictionary.
        """
        try:
            if key is None:
                return self.config
            return self.config.get(key, None)
        except Exception as e:
            logger.error(f"Error retrieving config key '{key}': {e}")
            return None

# Load environment variables from .env file
load_dotenv()

def validate_env_file() -> None:
    """
    Validate that all required environment variables are set.
    Raises ValueError if any required variable is missing or invalid.
    """
    required_vars = {
        'API_ID': 'Telegram API ID (get from https://my.telegram.org/apps)',
        'API_HASH': 'Telegram API Hash (get from https://my.telegram.org/apps)',
        'BOT_TOKEN': 'Bot Token (get from @BotFather)',
        'ADMIN_ID': 'Your Telegram User ID (get from @userinfobot)'
    }
    
    # CHANNEL_ID is optional - can be set later
    optional_vars = {
        'CHANNEL_ID': 'Channel ID or username for forwarding messages (optional)'
    }
    
    missing_vars = []
    invalid_vars = []
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        
        if not value or value in ['x', 'your_api_id_here', 'your_api_hash_here', 
                                    'your_bot_token_here', 'your_admin_user_id_here',
                                    'your_channel_id_or_username', '0']:
            missing_vars.append(f"  • {var_name}: {description}")
    
    # Check optional vars but don't fail validation
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if not value or value in ['x', 'your_channel_id_or_username', '0']:
            logger.warning(f"Optional variable '{var_name}' not set: {description}")
    
    if missing_vars:
        error_msg = (
            "\n❌ Environment Configuration Error!\n\n"
            "The following required environment variables are missing or invalid:\n"
            + "\n".join(missing_vars) +
            "\n\nPlease:\n"
            "1. Copy env.example to .env: cp env.example .env\n"
            "2. Edit .env and fill in your actual credentials\n"
            "3. Restart the bot\n"
        )
        logger.critical(error_msg)
        raise ValueError(error_msg)
    
    logger.info("✓ All required environment variables are configured")

def get_env_variable(name: str, default: Optional[Any] = None) -> Any:
    """
    Retrieve an environment variable with an optional default value.
    :param name: Name of the environment variable.
    :param default: Default value if the variable is not set.
    :return: Environment variable value or the default.
    """
    try:
        value = os.getenv(name)
        if value is None:
            logger.warning(f"Environment variable '{name}' not found. Using default value: {default}")
            return default
        return value
    except Exception as e:
        logger.error(f"Error retrieving environment variable '{name}': {e}")
        return default

def get_env_int(name: str, default: int = 0) -> int:
    """
    Retrieve an environment variable as an integer with a default value.
    :param name: Name of the environment variable.
    :param default: Default integer value if the variable is not set or invalid.
    :return: Integer value of the environment variable or the default.
    """
    try:
        value = get_env_variable(name, default=str(default))
        if value in ['x', 'your_api_id_here', 'your_admin_user_id_here', '0', '']:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

# Load essential configuration values from environment variables
API_ID = get_env_int('API_ID', default=0)
API_HASH = get_env_variable('API_HASH', default='x')
BOT_TOKEN = get_env_variable('BOT_TOKEN', default='x')
CHANNEL_ID = get_env_variable('CHANNEL_ID', default='x')
BOT_SESSION_NAME = get_env_variable('BOT_SESSION_NAME', default='BOT_SESSION')
ADMIN_ID = get_env_int('ADMIN_ID', default=0)
CLIENTS_JSON_PATH = str(get_env_variable('CLIENTS_JSON_PATH', default='clients.json'))
RATE_LIMIT_SLEEP = get_env_int('RATE_LIMIT_SLEEP', default=60)
GROUPS_BATCH_SIZE = get_env_int('GROUPS_BATCH_SIZE', default=10)
GROUPS_UPDATE_SLEEP = get_env_int('GROUPS_UPDATE_SLEEP', default=60)

# Load port configurations from environment variables
PORTS = {
    "HTTP": get_env_int('HTTP_PORT', default=80),
    "HTTPS": get_env_int('HTTPS_PORT', default=443),
    "TELEGRAM": get_env_int('TELEGRAM_PORT', default=443)
}

# Report check bot configuration
REPORT_CHECK_BOT = get_env_variable('REPORT_CHECK_BOT', default='')

# Validate environment configuration - only when bot starts, not at import time
# This allows tests to set environment variables via fixtures before validation
# Validation will be called explicitly in main.py or Telbot.__init__

