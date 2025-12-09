"""
Unit tests for ConfigManager class
"""
import pytest
import json
import os
import tempfile
import shutil
from src.Config import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager"""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file"""
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "test_config.json")
        yield config_path
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_init_with_default_config(self, temp_config_file):
        """Test ConfigManager initialization with default config"""
        manager = ConfigManager(temp_config_file)
        assert manager.filename == os.path.basename(temp_config_file)
        assert isinstance(manager.config, dict)
        assert "TARGET_GROUPS" in manager.config
        assert "KEYWORDS" in manager.config
        assert "IGNORE_USERS" in manager.config
        assert "clients" in manager.config

    def test_load_config_new_file(self, temp_config_file):
        """Test loading config from non-existent file"""
        if os.path.exists(temp_config_file):
            os.remove(temp_config_file)
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        assert isinstance(config, dict)
        assert config == manager.default_config

    def test_load_config_existing_file(self, temp_config_file):
        """Test loading config from existing file"""
        test_config = {
            "TARGET_GROUPS": [123],
            "KEYWORDS": ["test"],
            "IGNORE_USERS": [456],
            "clients": {"test": []}
        }
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        assert config["TARGET_GROUPS"] == [123]
        assert config["KEYWORDS"] == ["test"]
        assert config["IGNORE_USERS"] == [456]
        assert config["clients"] == {"test": []}

    def test_save_config(self, temp_config_file):
        """Test saving configuration"""
        manager = ConfigManager(temp_config_file)
        test_config = {
            "TARGET_GROUPS": [123],
            "KEYWORDS": ["test"],
            "IGNORE_USERS": [456],
            "clients": {"test": []}
        }
        manager.save_config(test_config)
        
        # Verify file was created and contains correct data
        assert os.path.exists(temp_config_file)
        with open(temp_config_file, 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
        assert loaded_config == test_config

    def test_update_config(self, temp_config_file):
        """Test updating a specific config key"""
        manager = ConfigManager(temp_config_file)
        manager.update_config("KEYWORDS", ["new", "keywords"])
        
        # Reload and verify
        config = manager.load_config()
        assert config["KEYWORDS"] == ["new", "keywords"]

    def test_merge_config(self, temp_config_file):
        """Test merging configurations"""
        manager = ConfigManager(temp_config_file)
        initial_config = {
            "KEYWORDS": ["old"],
            "IGNORE_USERS": [123]
        }
        manager.save_config(initial_config)
        
        new_config = {
            "KEYWORDS": ["new"],
            "TARGET_GROUPS": [456]
        }
        manager.merge_config(new_config)
        
        # Reload and verify
        config = manager.load_config()
        assert "new" in config["KEYWORDS"]
        assert "old" in config["KEYWORDS"]  # Lists should merge
        assert config["TARGET_GROUPS"] == [456]  # New key added
        assert config["IGNORE_USERS"] == [123]  # Existing preserved

    def test_get_config_all(self, temp_config_file):
        """Test getting all configuration"""
        manager = ConfigManager(temp_config_file)
        config = manager.get_config()
        assert isinstance(config, dict)
        assert "TARGET_GROUPS" in config

    def test_get_config_key(self, temp_config_file):
        """Test getting specific configuration key"""
        manager = ConfigManager(temp_config_file)
        test_config = {"KEYWORDS": ["test", "keywords"]}
        manager.save_config(test_config)
        
        keywords = manager.get_config("KEYWORDS")
        assert keywords == ["test", "keywords"]

    def test_get_config_nonexistent_key(self, temp_config_file):
        """Test getting non-existent configuration key"""
        manager = ConfigManager(temp_config_file)
        value = manager.get_config("NONEXISTENT_KEY")
        assert value is None

    def test_filename_sanitization(self):
        """Test filename sanitization to prevent path traversal"""
        # Test with dangerous filename
        dangerous_filename = "../../../etc/passwd"
        manager = ConfigManager(dangerous_filename)
        # Should sanitize to safe filename
        assert ".." not in manager.filename
        assert manager.filename.endswith('.json')

    def test_empty_file_handling(self, temp_config_file):
        """Test handling of empty config file"""
        # Create empty file
        with open(temp_config_file, 'w') as f:
            f.write("")
        
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        # Should return default config
        assert isinstance(config, dict)
        assert config == manager.default_config

    def test_invalid_json_handling(self, temp_config_file):
        """Test handling of invalid JSON"""
        # Create file with invalid JSON
        with open(temp_config_file, 'w') as f:
            f.write("invalid json {")
        
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        # Should return default config
        assert isinstance(config, dict)
        assert config == manager.default_config

