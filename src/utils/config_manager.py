import json
import logging
import os
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, filename: str = "clients.json", config: Dict[str, Any] = None):
        self.filename = filename
        self.default_config = {
            "TARGET_GROUPS": [],
            "KEYWORDS": [],
            "IGNORE_USERS": [],
            "clients": []
        }
        self.config = config if config is not None else self.load_config()

    #PASS
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from the JSON file."""
        logger.info(f"Loading config from {self.filename}")
        
        if not os.path.exists(self.filename):
            logger.warning(f"Config file {self.filename} does not exist. Creating a new one.")
            self.save_config()
            return self.default_config.copy()

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                logger.info("Config file loaded successfully")
                return {**self.default_config, **loaded_config}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON in {self.filename}: {e}")
            return self.default_config.copy()
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            return self.default_config.copy()

    #PASS
    def save_config(self, new_config: Dict[str, Any] = None) -> bool:
        """Save the current configuration to the JSON file."""
        logger.info("Saving config to file")
        
        if new_config:
            self.merge_config(new_config)

        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("Config saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving config to {self.filename}: {e}")
            return False

    #PASS
    def update_config(self, key: str, value: Any) -> bool:
        """Update a specific key in the configuration."""
        logger.info(f"Updating config key: {key}")
        
        if key not in self.config:
            logger.warning(f"Key {key} not found in config")
            return False
            
        self.config[key] = value
        return self.save_config()

    #PASS
    def merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge the new configuration with the existing configuration."""
        logger.info("Merging new configuration")
        
        for key, value in new_config.items():
            if key in self.config:
                if isinstance(self.config[key], list) and isinstance(value, list):
                    self.config[key] = list(dict.fromkeys(value))
                else:
                    self.config[key] = value
            else:
                self.config[key] = value

    #PASS
    def get_config(self, key: str = None) -> Union[Dict[str, Any], Any]:
        """Get the entire config or a specific key's value."""
        if key is None:
            return self.config
        return self.config.get(key)