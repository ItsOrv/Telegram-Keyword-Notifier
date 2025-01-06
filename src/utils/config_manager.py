import json
import logging
import os

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, filename="clients.json"):
        self.filename = filename
        self.default_config = {
            "TARGET_GROUPS": [],
            "KEYWORDS": [],
            "IGNORE_USERS": [],
            "clients": []  # اینجا کلید جدید clients اضافه شد
        }
        self.config = self.load_config()

    def load_config(self):
        """Load configuration from the JSON file."""
        logger.info("load_config in ConfigManager")
        if not os.path.exists(self.filename):
            logger.warning(f"Config file {self.filename} does not exist. Creating a new one.")
            self.save_config()  # ذخیره تنظیمات پیش‌فرض به عنوان فایل جدید
            return self.default_config.copy()  # کپی از دیکشنری پیش‌فرض ایجاد می‌کند

        try:
            with open(self.filename, 'r') as f:
                loaded_config = json.load(f)
                logger.info("Config file found!")
                # ترکیب دیکشنری‌های موجود و پیش‌فرض در صورت عدم وجود کلیدهایی در فایل
                combined_config = {**self.default_config, **loaded_config}
                return combined_config
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON in {self.filename}: {e}")
            return self.default_config.copy()

    def save_config(self):
        """Save the current configuration to the JSON file."""
        logger.info("save_config in ConfigManager")
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.config, f, indent=4)
                logger.info("JSON file saved successfully")
        except Exception as e:
            logger.error(f"Error saving config to {self.filename}: {e}")

    def update_config(self, key, value):
        """Update a specific key in the configuration."""
        logger.info(f"Updating config for key: {key}")
        if key in self.config:
            self.config[key] = value
            self.save_config()
            logger.info(f"Config updated: {key} = {value}")
        else:
            logger.warning(f"Key {key} not found in config.")
