import json
import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> dict:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {'clients': [], 'IGNORE_USERS': [], 'KEYWORDS': []}
        except json.JSONDecodeError as e:
            logger.error(f"Error loading config: {e}")
            return {'clients': [], 'IGNORE_USERS': [], 'KEYWORDS': []}

    def save_config(self) -> None:
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
