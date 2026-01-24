"""
Pytest configuration and fixtures for comprehensive testing
"""
import pytest
import asyncio
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telethon import TelegramClient, events, Button
from telethon.tl.types import User, Channel, Chat

# Test configuration
TEST_CONFIG = {
    "TARGET_GROUPS": [],
    "KEYWORDS": ["test"],
    "IGNORE_USERS": [123456789],
    "clients": {}
}

TEST_ENV_VARS = {
    'API_ID': '12345',
    'API_HASH': 'test_hash',
    'BOT_TOKEN': 'test_token',
    'ADMIN_ID': '123456789',
    'CHANNEL_ID': 'test_channel',
    'CLIENTS_JSON_PATH': 'test_clients.json',
    'RATE_LIMIT_SLEEP': '1',
    'GROUPS_BATCH_SIZE': '5',
    'GROUPS_UPDATE_SLEEP': '1'
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file"""
    config_path = os.path.join(temp_dir, "test_clients.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(TEST_CONFIG, f, indent=4)
    return config_path

@pytest.fixture(autouse=True, scope='function')
def reset_module_state():
    """Reset module-level state between tests"""
    # This fixture runs automatically before each test
    # Reset any module-level state that might be shared
    import importlib
    import sys
    
    # Save original modules
    original_modules = {}
    modules_to_reload = ['src.Config', 'src.Handlers']
    
    # Reload modules to reset any cached values
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    yield
    
    # Cleanup after test - reload again to ensure clean state
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])

@pytest.fixture(scope='function')
def mock_tbot():
    """Create a mock TelegramBot instance"""
    from types import SimpleNamespace
    mock = SimpleNamespace()
    # Use fresh copies for each test to avoid state sharing
    mock.config = TEST_CONFIG.copy()
    mock.active_clients = {}
    mock.active_clients_lock = asyncio.Lock()
    mock.handlers = {}
    mock._conversations = {}
    mock._conversations_lock = asyncio.Lock()
    mock.config_manager = MagicMock()
    mock.config_manager.save_config = MagicMock()
    mock.config_manager.load_config = MagicMock(return_value=TEST_CONFIG.copy())
    mock.tbot = AsyncMock()
    mock.tbot.send_message = AsyncMock()
    mock.notify_admin = AsyncMock()
    mock.client_manager = MagicMock()
    # Add account_handler and monitor for integration tests
    mock.account_handler = MagicMock()
    mock.monitor = MagicMock()
    # Ensure tbot.tbot exists for AccountHandler
    if not hasattr(mock.tbot, 'tbot'):
        mock.tbot.tbot = mock.tbot
    return mock

@pytest.fixture
def mock_telegram_client():
    """Create a mock TelegramClient"""
    mock = AsyncMock(spec=TelegramClient)
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_user_authorized = AsyncMock(return_value=True)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.start = AsyncMock()
    mock.send_code_request = AsyncMock()
    mock.sign_in = AsyncMock()
    mock.get_entity = AsyncMock()
    mock.join_chat = AsyncMock()
    mock.leave_chat = AsyncMock()
    mock.send_message = AsyncMock()
    mock.get_messages = AsyncMock()
    mock.iter_dialogs = AsyncMock()
    mock.session = MagicMock()
    mock.session.filename = "test_session.session"
    mock.session.save = MagicMock()
    mock.on = MagicMock(return_value=MagicMock())
    mock.remove_event_handler = MagicMock()
    return mock

@pytest.fixture
def mock_event():
    """Create a mock Telegram event"""
    mock = AsyncMock()
    mock.sender_id = 123456789
    mock.chat_id = 123456789
    mock.message = MagicMock()
    mock.message.text = "test message"
    mock.message.id = 1
    mock.event = MagicMock()
    mock.data = b'test_data'
    mock.respond = AsyncMock()
    mock.edit = AsyncMock()
    mock.delete = AsyncMock()
    mock.answer = AsyncMock()
    
    # Mock sender
    mock_sender = MagicMock(spec=User)
    mock_sender.id = 123456789
    mock_sender.first_name = "Test"
    mock_sender.last_name = "User"
    mock.get_sender = AsyncMock(return_value=mock_sender)
    
    # Mock chat
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = 123456789
    mock_chat.title = "Test Chat"
    mock_chat.username = "testchat"
    mock.get_chat = AsyncMock(return_value=mock_chat)
    
    return mock

class MockCallbackEvent:
    """Mock callback event for testing"""
    def __init__(self):
        self.sender_id = 123456789
        self.chat_id = 123456789
        self.data = b'add_account'
        self.message = None
        self.respond = AsyncMock()
        self.edit = AsyncMock()
        self.delete = AsyncMock()
        self.answer = AsyncMock()

@pytest.fixture(scope='function')
def mock_callback_event():
    """Create a mock callback query event"""
    return MockCallbackEvent()

@pytest.fixture
def mock_new_message_event():
    """Create a mock new message event"""
    mock = AsyncMock()
    mock.sender_id = 123456789
    mock.chat_id = 123456789
    mock.message = MagicMock()
    mock.message.text = "test"
    mock.message.id = 1
    mock.out = False
    mock.chat_id = -1001234567890  # Group chat ID
    mock.id = 1
    
    # Mock sender
    mock_sender = MagicMock(spec=User)
    mock_sender.id = 987654321
    mock_sender.first_name = "Test"
    mock_sender.last_name = "Sender"
    mock.get_sender = AsyncMock(return_value=mock_sender)
    
    # Mock chat
    mock_chat = MagicMock(spec=Channel)
    mock_chat.id = -1001234567890
    mock_chat.title = "Test Channel"
    mock_chat.username = "testchannel"
    mock_chat.broadcast = False
    mock.get_chat = AsyncMock(return_value=mock_chat)
    
    mock.respond = AsyncMock()
    return mock

@pytest.fixture(scope='function')
def mock_admin_event(mock_event):
    """Create a mock event from admin"""
    mock_event.sender_id = 123456789  # Admin ID from TEST_ENV_VARS
    return mock_event

@pytest.fixture(scope='function')
def mock_non_admin_event(mock_event):
    """Create a mock event from non-admin"""
    mock_event.sender_id = 999999999  # Non-admin ID
    return mock_event

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for all tests"""
    for key, value in TEST_ENV_VARS.items():
        monkeypatch.setenv(key, value)

@pytest.fixture
def mock_config_manager(temp_config_file):
    """Create a mock ConfigManager"""
    from src.Config import ConfigManager
    manager = ConfigManager(temp_config_file)
    return manager

@pytest.fixture
def sample_keywords():
    """Sample keywords for testing"""
    return ["test", "keyword", "sample"]

@pytest.fixture
def sample_ignore_users():
    """Sample ignore users for testing"""
    return [123456789, 987654321]

@pytest.fixture
def sample_clients():
    """Sample client sessions for testing"""
    return {
        "test_session1": [123456789, 987654321],
        "test_session2": [111222333]
    }

@pytest.fixture
def mock_actions():
    """Create a mock Actions instance"""
    from src.actions import Actions
    mock_tbot = mock_tbot()
    actions = Actions(mock_tbot)
    return actions

@pytest.fixture
def mock_session_manager(mock_tbot):
    """Create a mock SessionManager"""
    from src.Client import SessionManager
    manager = SessionManager(
        TEST_CONFIG.copy(),
        mock_tbot.active_clients,
        mock_tbot
    )
    return manager

@pytest.fixture
def mock_account_handler(mock_tbot):
    """Create a mock AccountHandler"""
    from src.Client import AccountHandler
    handler = AccountHandler(mock_tbot)
    return handler

@pytest.fixture
def mock_message_handler(mock_tbot):
    """Create a mock MessageHandler"""
    from src.Handlers import MessageHandler
    handler = MessageHandler(mock_tbot)
    return handler

@pytest.fixture
def mock_callback_handler(mock_tbot):
    """Create a mock CallbackHandler"""
    from src.Handlers import CallbackHandler
    handler = CallbackHandler(mock_tbot)
    return handler

@pytest.fixture
def mock_monitor(mock_tbot):
    """Create a mock Monitor"""
    from src.Monitor import Monitor
    monitor = Monitor(mock_tbot)
    return monitor

