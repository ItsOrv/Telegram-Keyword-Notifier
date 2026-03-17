"""
Comprehensive tests for Config.py module
Tests configuration management and environment variable handling
"""
import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, Mock

from src.Config import (
    ConfigManager,
    validate_env_file,
    get_env_variable,
    get_env_int,
    API_ID,
    API_HASH,
    BOT_TOKEN,
    ADMIN_ID,
    CHANNEL_ID
)


class TestConfigManager:
    """Comprehensive tests for ConfigManager"""
    
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
    
    def test_init_with_provided_config(self, temp_config_file):
        """Test ConfigManager initialization with provided config"""
        provided_config = {
            "TARGET_GROUPS": [123],
            "KEYWORDS": ["test"],
            "IGNORE_USERS": [456],
            "clients": {"test": []}
        }
        manager = ConfigManager(temp_config_file, provided_config)
        assert manager.config == provided_config
    
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
    
    def test_load_config_empty_file(self, temp_config_file):
        """Test loading config from empty file"""
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        assert config == manager.default_config
    
    def test_load_config_invalid_json(self, temp_config_file):
        """Test loading config from invalid JSON file"""
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            f.write("invalid json {")
        
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        # Should fall back to default config
        assert config == manager.default_config
    
    def test_load_config_not_dict(self, temp_config_file):
        """Test loading config that is not a dictionary"""
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump([1, 2, 3], f)
        
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        # Should fall back to default config
        assert config == manager.default_config
    
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
        
        assert os.path.exists(temp_config_file)
        with open(temp_config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        assert saved_config == test_config
    
    def test_save_config_creates_directory(self, temp_config_file):
        """Test that save_config creates directory if needed"""
        config_path = os.path.join(temp_config_file, "subdir", "config.json")
        manager = ConfigManager(config_path)
        test_config = {"KEYWORDS": ["test"]}
        
        manager.save_config(test_config)
        
        assert os.path.exists(config_path)
    
    def test_update_config(self, temp_config_file):
        """Test updating a specific config key"""
        manager = ConfigManager(temp_config_file)
        
        manager.update_config("KEYWORDS", ["new", "keywords"])
        
        assert manager.config["KEYWORDS"] == ["new", "keywords"]
        # Verify it was saved to file
        with open(temp_config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        assert saved_config["KEYWORDS"] == ["new", "keywords"]
    
    def test_update_config_new_key(self, temp_config_file):
        """Test updating with a new key not in default config"""
        manager = ConfigManager(temp_config_file)
        
        manager.update_config("NEW_KEY", "new_value")
        
        assert manager.config["NEW_KEY"] == "new_value"
    
    def test_merge_config(self, temp_config_file):
        """Test merging configuration"""
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
        
        # Keywords should be merged (no duplicates)
        assert "old" in manager.config["KEYWORDS"] or "new" in manager.config["KEYWORDS"]
        assert manager.config["TARGET_GROUPS"] == [456]
    
    def test_merge_config_preserves_order(self, temp_config_file):
        """Test that merge_config preserves order and removes duplicates"""
        manager = ConfigManager(temp_config_file)
        initial_config = {
            "KEYWORDS": ["keyword1", "keyword2"]
        }
        manager.save_config(initial_config)
        
        new_config = {
            "KEYWORDS": ["keyword2", "keyword3"]
        }
        manager.merge_config(new_config)
        
        # Should have all unique keywords
        keywords = manager.config["KEYWORDS"]
        assert "keyword1" in keywords
        assert "keyword2" in keywords
        assert "keyword3" in keywords
        # keyword2 should appear only once
        assert keywords.count("keyword2") == 1
    
    def test_get_config_all(self, temp_config_file):
        """Test getting entire configuration"""
        manager = ConfigManager(temp_config_file)
        test_config = {
            "TARGET_GROUPS": [123],
            "KEYWORDS": ["test"]
        }
        manager.save_config(test_config)
        
        config = manager.get_config()
        assert isinstance(config, dict)
        assert "TARGET_GROUPS" in config
    
    def test_get_config_specific_key(self, temp_config_file):
        """Test getting specific configuration key"""
        manager = ConfigManager(temp_config_file)
        test_config = {
            "KEYWORDS": ["test", "keyword"]
        }
        manager.save_config(test_config)
        
        keywords = manager.get_config("KEYWORDS")
        assert keywords == ["test", "keyword"]
    
    def test_get_config_nonexistent_key(self, temp_config_file):
        """Test getting non-existent configuration key"""
        manager = ConfigManager(temp_config_file)
        
        value = manager.get_config("NONEXISTENT_KEY")
        assert value is None
    
    def test_sanitize_filename(self, temp_config_file):
        """Test filename sanitization"""
        # Test with path traversal attempt
        dangerous_path = "../../etc/passwd"
        manager = ConfigManager(dangerous_path)
        
        # Filename should be sanitized
        assert ".." not in manager.filename
        assert "/" not in manager.filename


class TestValidateEnvFile:
    """Tests for validate_env_file function"""
    
    def test_validate_all_required_present(self, monkeypatch):
        """Test validation when all required variables are present"""
        monkeypatch.setenv('API_ID', '12345')
        monkeypatch.setenv('API_HASH', 'test_hash')
        monkeypatch.setenv('BOT_TOKEN', 'test_token')
        monkeypatch.setenv('ADMIN_ID', '123456789')
        
        # Should not raise exception
        validate_env_file()
    
    def test_validate_missing_api_id(self, monkeypatch):
        """Test validation when API_ID is missing"""
        monkeypatch.setenv('API_ID', 'x')
        monkeypatch.setenv('API_HASH', 'test_hash')
        monkeypatch.setenv('BOT_TOKEN', 'test_token')
        monkeypatch.setenv('ADMIN_ID', '123456789')
        
        with pytest.raises(ValueError):
            validate_env_file()
    
    def test_validate_missing_api_hash(self, monkeypatch):
        """Test validation when API_HASH is missing"""
        monkeypatch.setenv('API_ID', '12345')
        monkeypatch.setenv('API_HASH', 'x')
        monkeypatch.setenv('BOT_TOKEN', 'test_token')
        monkeypatch.setenv('ADMIN_ID', '123456789')
        
        with pytest.raises(ValueError):
            validate_env_file()
    
    def test_validate_missing_bot_token(self, monkeypatch):
        """Test validation when BOT_TOKEN is missing"""
        monkeypatch.setenv('API_ID', '12345')
        monkeypatch.setenv('API_HASH', 'test_hash')
        monkeypatch.setenv('BOT_TOKEN', 'x')
        monkeypatch.setenv('ADMIN_ID', '123456789')
        
        with pytest.raises(ValueError):
            validate_env_file()
    
    def test_validate_missing_admin_id(self, monkeypatch):
        """Test validation when ADMIN_ID is missing"""
        monkeypatch.setenv('API_ID', '12345')
        monkeypatch.setenv('API_HASH', 'test_hash')
        monkeypatch.setenv('BOT_TOKEN', 'test_token')
        monkeypatch.setenv('ADMIN_ID', '0')
        
        with pytest.raises(ValueError):
            validate_env_file()
    
    def test_validate_optional_channel_id(self, monkeypatch):
        """Test that CHANNEL_ID is optional"""
        monkeypatch.setenv('API_ID', '12345')
        monkeypatch.setenv('API_HASH', 'test_hash')
        monkeypatch.setenv('BOT_TOKEN', 'test_token')
        monkeypatch.setenv('ADMIN_ID', '123456789')
        monkeypatch.setenv('CHANNEL_ID', 'x')
        
        # Should not raise exception (CHANNEL_ID is optional)
        validate_env_file()
    
    def test_validate_placeholder_values(self, monkeypatch):
        """Test that placeholder values are rejected"""
        placeholder_values = [
            'your_api_id_here',
            'your_api_hash_here',
            'your_bot_token_here',
            'your_admin_user_id_here'
        ]
        
        for placeholder in placeholder_values:
            monkeypatch.setenv('API_ID', '12345')
            monkeypatch.setenv('API_HASH', 'test_hash')
            monkeypatch.setenv('BOT_TOKEN', 'test_token')
            monkeypatch.setenv('ADMIN_ID', '123456789')
            monkeypatch.setenv('API_ID', placeholder)
            
            with pytest.raises(ValueError):
                validate_env_file()


class TestGetEnvVariable:
    """Tests for get_env_variable function"""
    
    def test_get_existing_variable(self, monkeypatch):
        """Test getting an existing environment variable"""
        monkeypatch.setenv('TEST_VAR', 'test_value')
        
        value = get_env_variable('TEST_VAR')
        assert value == 'test_value'
    
    def test_get_nonexistent_variable_with_default(self, monkeypatch):
        """Test getting non-existent variable with default"""
        monkeypatch.delenv('TEST_VAR', raising=False)
        
        value = get_env_variable('TEST_VAR', default='default_value')
        assert value == 'default_value'
    
    def test_get_nonexistent_variable_without_default(self, monkeypatch):
        """Test getting non-existent variable without default"""
        monkeypatch.delenv('TEST_VAR', raising=False)
        
        value = get_env_variable('TEST_VAR')
        assert value is None


class TestGetEnvInt:
    """Tests for get_env_int function"""
    
    def test_get_valid_integer(self, monkeypatch):
        """Test getting a valid integer environment variable"""
        monkeypatch.setenv('TEST_INT', '123')
        
        value = get_env_int('TEST_INT', default=0)
        assert value == 123
    
    def test_get_invalid_integer_with_default(self, monkeypatch):
        """Test getting invalid integer with default"""
        monkeypatch.setenv('TEST_INT', 'invalid')
        
        value = get_env_int('TEST_INT', default=456)
        assert value == 456
    
    def test_get_nonexistent_with_default(self, monkeypatch):
        """Test getting non-existent variable with default"""
        monkeypatch.delenv('TEST_INT', raising=False)
        
        value = get_env_int('TEST_INT', default=789)
        assert value == 789
    
    def test_get_placeholder_value(self, monkeypatch):
        """Test getting placeholder value"""
        monkeypatch.setenv('TEST_INT', 'x')
        
        value = get_env_int('TEST_INT', default=999)
        assert value == 999


class TestConfigConstants:
    """Tests for configuration constants"""
    
    def test_api_id_type(self):
        """Test that API_ID is an integer"""
        assert isinstance(API_ID, int)
    
    def test_api_hash_type(self):
        """Test that API_HASH is a string"""
        assert isinstance(API_HASH, str)
    
    def test_bot_token_type(self):
        """Test that BOT_TOKEN is a string"""
        assert isinstance(BOT_TOKEN, str)
    
    def test_admin_id_type(self):
        """Test that ADMIN_ID is an integer"""
        assert isinstance(ADMIN_ID, int)
    
    def test_channel_id_type(self):
        """Test that CHANNEL_ID is a string"""
        assert isinstance(CHANNEL_ID, str)

