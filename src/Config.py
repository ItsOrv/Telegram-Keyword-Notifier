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
            self.filename = filename
            self.default_config = {
                "TARGET_GROUPS": [],  # List of target groups for the bot
                "KEYWORDS": [],       # List of keywords for filtering
                "IGNORE_USERS": [],   # List of user IDs to ignore
                "clients": []         # List of client configurations
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
            if not os.path.exists(self.filename) or os.path.getsize(self.filename) == 0:
                logger.warning(f"Config file '{self.filename}' not found or empty. Creating a new file with default settings.")
                self.save_config(self.default_config)
                return self.default_config.copy()

            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                if not isinstance(loaded_config, dict):
                    raise ValueError("Config file must contain a JSON object.")
                logger.info("Config file loaded successfully.")
                # Merge loaded configuration with default values
                return {**self.default_config, **loaded_config}
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.error(f"Error loading config file '{self.filename}': {e}. Falling back to default config.")
            return self.default_config.copy()

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save the current configuration to the JSON file.
        :param config: Configuration dictionary to save.
        """
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("Configuration saved successfully.")
        except OSError as e:
            logger.error(f"Failed to save config file '{self.filename}': {e}")

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
            for key, value in new_config.items():
                if key in self.config and isinstance(self.config[key], list) and isinstance(value, list):
                    # Combine lists while avoiding duplicates
                    self.config[key] = list(set(self.config[key] + value))
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

# Load essential configuration values from environment variables
API_ID = int(get_env_variable('API_ID', default=0))
API_HASH = get_env_variable('API_HASH', default='x')
BOT_TOKEN = get_env_variable('BOT_TOKEN', default='x')
CHANNEL_ID = get_env_variable('CHANNEL_ID', default='x')
BOT_SESSION_NAME = get_env_variable('BOT_SESSION_NAME', default='BOT_SESSION')
ADMIN_ID = int(get_env_variable('ADMIN_ID', default=0))
CLIENTS_JSON_PATH = str(get_env_variable('CLIENTS_JSON_PATH', default='clients.json'))
RATE_LIMIT_SLEEP = int(get_env_variable('RATE_LIMIT_SLEEP', default=60))
GROUPS_BATCH_SIZE = int(get_env_variable('GROUPS_BATCH_SIZE', default=10))
GROUPS_UPDATE_SLEEP = int(get_env_variable('GROUPS_UPDATE_SLEEP', default=60))

# Load port configurations from environment variables
PORTS = {
    "HTTP": int(get_env_variable('HTTP_PORT', default=80)),
    "HTTPS": int(get_env_variable('HTTPS_PORT', default=443)),
    "TELEGRAM": int(get_env_variable('TELEGRAM_PORT', default=443))
}

