import json
import logging
import os

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from the JSON file."""
        print("load_config in ConfigManager")
        if not os.path.exists(self.filename):
            logger.warning(f"Config file {self.filename} does not exist. Creating a new one.")
            return {"TARGET_GROUPS": [], "KEYWORDS": [], "IGNORE_USERS": []}
        
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON in {self.filename}: {e}")
            return {}

    def save_config(self):
        """Save the current configuration to the JSON file."""
        print("save_config in ConfigManager")
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config to {self.filename}: {e}")

    def update_config(self, key, value):
        """Update a specific key in the configuration."""
        print("update_config in ConfigManager")
        self.config[key] = value
        self.save_config()
