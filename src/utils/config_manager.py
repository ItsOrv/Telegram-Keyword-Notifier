import json
import logging
import os

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, filename="clients.json", config=None):
        self.filename = filename
        self.default_config = {
            "TARGET_GROUPS": [],
            "KEYWORDS": [],
            "IGNORE_USERS": [],
            "clients": []  # اینجا کلید جدید clients اضافه شد
        }
        if config is not None:
            self.config = config
        else:
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

    def save_config(self, new_config=None):
        """Save the current configuration to the JSON file, merging new configuration if provided."""
        logger.info("save_config in ConfigManager")
        if new_config:
            self.merge_config(new_config)

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

    def merge_config(self, new_config):
        """Merge the new configuration with the existing configuration."""
        logger.info("Merging new configuration with existing configuration")
        for key, value in new_config.items():
            if key in self.config:
                if isinstance(self.config[key], list):
                    self.config[key] = list(set(self.config[key]) & set(value))  # حذف عناصر حذف شده
                else:
                    self.config[key] = value
            else:
                self.config[key] = value

    def load_json_config(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        else:
            return {'clients': [], 'IGNORE_USERS': [], 'KEYWORDS': []}

    def update_json_config(self, config):
        with open(self.filename, 'w') as f:
            json.dump(config, f, indent=4)
