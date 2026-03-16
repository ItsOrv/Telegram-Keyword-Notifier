"""
Comprehensive tests for Client.py module
Tests SessionManager and AccountHandler with all edge cases
"""
import pytest
import asyncio
import os
import tempfile
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, SessionRevokedError
from telethon.tl.types import User, Channel, Chat

from src.Client import SessionManager, AccountHandler
from src.Config import ConfigManager


@pytest.mark.asyncio
class TestSessionManager:
    """Comprehensive tests for SessionManager"""
    
    async def test_initialization(self, mock_tbot, temp_config_file):
        """Test SessionManager initialization"""
        config = {"clients": {}}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        assert manager.config == config
        assert manager.active_clients == mock_tbot.active_clients
        assert manager.tbot == mock_tbot.tbot
    
    async def test_detect_sessions_empty_config(self, mock_tbot):
        """Test detecting sessions with empty config"""
        config = {"clients": {}}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        await manager.detect_sessions()
        assert len(mock_tbot.active_clients) == 0
    
    async def test_detect_sessions_with_clients(self, mock_tbot, mock_telegram_client):
        """Test detecting sessions with existing clients"""
        config = {"clients": {"session1": [], "session2": []}}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
            await manager.detect_sessions()
            
            assert len(mock_tbot.active_clients) == 2
            assert "session1" in mock_tbot.active_clients
            assert "session2" in mock_tbot.active_clients
    
    async def test_detect_sessions_invalid_name(self, mock_tbot):
        """Test detecting sessions with invalid session name"""
        config = {"clients": {"../invalid": [], "valid_session": []}}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        with patch('src.Client.TelegramClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            await manager.detect_sessions()
            
            # Invalid session should be skipped
            assert "../invalid" not in mock_tbot.active_clients
    
    async def test_start_saved_clients_all_authorized(self, mock_tbot, mock_telegram_client):
        """Test starting all authorized clients"""
        config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        mock_telegram_client.is_connected = Mock(return_value=False)
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.get_dialogs = AsyncMock(return_value=[])
        
        with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
            await manager.start_saved_clients()
            
            assert len(mock_tbot.active_clients) == 1
            mock_telegram_client.connect.assert_called_once()
    
    async def test_start_saved_clients_unauthorized(self, mock_tbot, mock_telegram_client):
        """Test starting unauthorized clients"""
        config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        mock_telegram_client.is_connected = Mock(return_value=False)
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=False)
        mock_telegram_client.get_dialogs = AsyncMock(side_effect=SessionRevokedError())
        
        with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
            with patch('src.Client.get_safe_session_file_path', return_value="session1.session"):
                with patch('os.path.exists', return_value=True):
                    with patch('os.remove'):
                        await manager.start_saved_clients()
                        
                        # Session should be removed
                        assert "session1" not in mock_tbot.active_clients
    
    async def test_start_saved_clients_flood_wait(self, mock_tbot, mock_telegram_client):
        """Test handling FloodWaitError during start"""
        config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        mock_telegram_client.is_connected = Mock(return_value=False)
        mock_telegram_client.is_user_authorized = AsyncMock(side_effect=FloodWaitError(seconds=1))
        
        with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
            await manager.start_saved_clients()
            
            # Should handle flood wait gracefully
            assert True  # Test passes if no exception
    
    async def test_disconnect_all_clients(self, mock_tbot, mock_telegram_client):
        """Test disconnecting all clients"""
        mock_tbot.active_clients = {
            "session1": mock_telegram_client,
            "session2": mock_telegram_client
        }
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.cleanup_client_handlers = Mock()
        
        config = {"clients": {}}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        await manager.disconnect_all_clients()
        
        assert len(mock_tbot.active_clients) == 0
        assert mock_telegram_client.disconnect.call_count == 2
    
    async def test_delete_session(self, mock_tbot, mock_telegram_client):
        """Test deleting a session"""
        config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {"session1": mock_telegram_client}
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.cleanup_client_handlers = Mock()
        
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        with patch('src.Client.get_safe_session_file_path', return_value="session1.session"):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    await manager.delete_session("session1")
                    
                    assert "session1" not in mock_tbot.active_clients
                    assert "session1" not in config["clients"]
    
    async def test_show_inactive_accounts_empty(self, mock_tbot, mock_event):
        """Test showing inactive accounts when none exist"""
        config = {"clients": {}, "inactive_accounts": {}}
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        await manager.show_inactive_accounts(mock_event)
        
        mock_event.respond.assert_called_once()
        assert "no inactive accounts" in mock_event.respond.call_args[0][0].lower()
    
    async def test_show_inactive_accounts_with_data(self, mock_tbot, mock_event):
        """Test showing inactive accounts with data"""
        import time
        config = {
            "clients": {},
            "inactive_accounts": {
                "session1": {
                    "phone": "+1234567890",
                    "reason": "auth_error",
                    "last_seen": time.time(),
                    "error_details": "Session revoked"
                }
            }
        }
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        await manager.show_inactive_accounts(mock_event)
        
        mock_event.respond.assert_called_once()
        response = mock_event.respond.call_args[0][0]
        assert "session1" in response or "+1234567890" in response
    
    async def test_reactivate_account_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test reactivating an inactive account"""
        config = {
            "clients": {},
            "inactive_accounts": {"session1": {"phone": "+1234567890", "reason": "auth_error"}}
        }
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.get_me = AsyncMock(return_value=Mock(id=123, first_name="Test"))
        
        with patch('src.Client.get_safe_session_file_path', return_value="session1.session"):
            with patch('os.path.exists', return_value=True):
                with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
                    with patch('src.Client.sanitize_session_name', return_value="session1"):
                        await manager.reactivate_account(mock_event, "session1")
                        
                        assert "session1" not in config.get("inactive_accounts", {})
                        mock_event.respond.assert_called()
    
    async def test_reactivate_account_failure(self, mock_tbot, mock_event, mock_telegram_client):
        """Test reactivating account that fails"""
        config = {
            "clients": {},
            "inactive_accounts": {"session1": {"phone": "+1234567890", "reason": "auth_error"}}
        }
        manager = SessionManager(config, mock_tbot.active_clients, mock_tbot.tbot)
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=False)
        
        with patch('src.Client.get_safe_session_file_path', return_value="session1.session"):
            with patch('os.path.exists', return_value=True):
                with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
                    with patch('src.Client.sanitize_session_name', return_value="session1"):
                        await manager.reactivate_account(mock_event, "session1")
                        
                        mock_event.respond.assert_called()


@pytest.mark.asyncio
class TestAccountHandler:
    """Comprehensive tests for AccountHandler"""
    
    async def test_initialization(self, mock_tbot):
        """Test AccountHandler initialization"""
        handler = AccountHandler(mock_tbot)
        assert handler.tbot == mock_tbot
        assert handler.SessionManager == mock_tbot.client_manager
    
    async def test_add_account(self, mock_tbot, mock_event):
        """Test adding account"""
        handler = AccountHandler(mock_tbot)
        
        with patch('src.Client.prompt_for_input', new_callable=AsyncMock):
            await handler.add_account(mock_event)
            
            mock_event.respond.assert_called()
    
    async def test_phone_number_handler_valid(self, mock_tbot, mock_event, mock_telegram_client):
        """Test phone number handler with valid number"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "+1234567890"
        mock_event.chat_id = 123
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=False)
        mock_telegram_client.send_code_request = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
            with patch('src.Client.sanitize_session_name', return_value="+1234567890"):
                await handler.phone_number_handler(mock_event)
                
                assert mock_tbot.handlers.get('temp_client') is not None
                assert mock_tbot.handlers.get('temp_phone') == "+1234567890"
                mock_telegram_client.send_code_request.assert_called_once()
    
    async def test_phone_number_handler_invalid(self, mock_tbot, mock_event):
        """Test phone number handler with invalid number"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "invalid"
        mock_event.chat_id = 123
        
        mock_tbot.tbot.send_message = AsyncMock()
        
        await handler.phone_number_handler(mock_event)
        
        mock_tbot.tbot.send_message.assert_called()
        assert "invalid" in mock_tbot.tbot.send_message.call_args[0][0].lower()
    
    async def test_phone_number_handler_already_authorized(self, mock_tbot, mock_event, mock_telegram_client):
        """Test phone number handler when already authorized"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "+1234567890"
        mock_event.chat_id = 123
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.get_me = AsyncMock(return_value=Mock(id=123, first_name="Test", username="test"))
        
        with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
            with patch('src.Client.sanitize_session_name', return_value="+1234567890"):
                with patch.object(handler, 'finalize_client_setup', new_callable=AsyncMock):
                    await handler.phone_number_handler(mock_event)
                    
                    handler.finalize_client_setup.assert_called_once()
    
    async def test_code_handler_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test code handler with successful verification"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "12345"
        mock_event.chat_id = 123
        
        mock_tbot.handlers = {
            'temp_client': mock_telegram_client,
            'temp_phone': "+1234567890"
        }
        mock_telegram_client.sign_in = AsyncMock()
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.get_me = AsyncMock(return_value=Mock(id=123, first_name="Test", username="test"))
        mock_tbot.tbot.send_message = AsyncMock()
        mock_tbot.tbot.send_message.return_value = AsyncMock()
        mock_tbot.tbot.send_message.return_value.delete = AsyncMock()
        
        with patch.object(handler, 'finalize_client_setup', new_callable=AsyncMock):
            await handler.code_handler(mock_event)
            
            mock_telegram_client.sign_in.assert_called_once()
            handler.finalize_client_setup.assert_called_once()
    
    async def test_code_handler_password_needed(self, mock_tbot, mock_event, mock_telegram_client):
        """Test code handler when password is needed"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "12345"
        mock_event.chat_id = 123
        
        mock_tbot.handlers = {
            'temp_client': mock_telegram_client,
            'temp_phone': "+1234567890"
        }
        mock_telegram_client.sign_in = AsyncMock(side_effect=SessionPasswordNeededError())
        mock_tbot.tbot.send_message = AsyncMock()
        
        await handler.code_handler(mock_event)
        
        assert mock_tbot._conversations[123] == 'password_handler'
        mock_tbot.tbot.send_message.assert_called()
    
    async def test_code_handler_flood_wait(self, mock_tbot, mock_event, mock_telegram_client):
        """Test code handler with FloodWaitError"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "12345"
        mock_event.chat_id = 123
        
        mock_tbot.handlers = {
            'temp_client': mock_telegram_client,
            'temp_phone': "+1234567890"
        }
        mock_telegram_client.sign_in = AsyncMock(side_effect=FloodWaitError(seconds=60))
        mock_tbot.tbot.send_message = AsyncMock()
        
        await handler.code_handler(mock_event)
        
        mock_tbot.tbot.send_message.assert_called()
        assert 'temp_client' not in mock_tbot.handlers
    
    async def test_password_handler_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test password handler with successful verification"""
        handler = AccountHandler(mock_tbot)
        mock_event.message.text = "password123"
        mock_event.chat_id = 123
        
        mock_tbot.handlers = {
            'temp_client': mock_telegram_client,
            'temp_phone': "+1234567890"
        }
        mock_telegram_client.sign_in = AsyncMock()
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.get_me = AsyncMock(return_value=Mock(id=123, first_name="Test", username="test"))
        mock_tbot.tbot.send_message = AsyncMock()
        mock_tbot.tbot.send_message.return_value = AsyncMock()
        mock_tbot.tbot.send_message.return_value.delete = AsyncMock()
        
        with patch.object(handler, 'finalize_client_setup', new_callable=AsyncMock):
            await handler.password_handler(mock_event)
            
            mock_telegram_client.sign_in.assert_called_once()
            handler.finalize_client_setup.assert_called_once()
    
    async def test_finalize_client_setup_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test finalizing client setup successfully"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.get_me = AsyncMock(return_value=Mock(id=123, first_name="Test", username="test"))
        mock_telegram_client.session.save = Mock()
        mock_tbot.config = {"clients": {}}
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        mock_tbot.active_clients = {}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.process_messages_for_client = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        with patch('src.Client.sanitize_session_name', return_value="+1234567890"):
            await handler.finalize_client_setup(mock_telegram_client, "+1234567890", 123)
            
            assert "+1234567890" in mock_tbot.active_clients
            assert "+1234567890" in mock_tbot.config["clients"]
            mock_tbot.tbot.send_message.assert_called()
    
    async def test_finalize_client_setup_not_authorized(self, mock_tbot, mock_event, mock_telegram_client):
        """Test finalizing setup when not authorized"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=False)
        mock_tbot.tbot.send_message = AsyncMock()
        
        await handler.finalize_client_setup(mock_telegram_client, "+1234567890", 123)
        
        mock_tbot.tbot.send_message.assert_called()
        assert 'temp_client' not in mock_tbot.handlers
    
    async def test_cleanup_temp_handlers(self, mock_tbot):
        """Test cleaning up temporary handlers"""
        handler = AccountHandler(mock_tbot)
        mock_tbot.handlers = {
            'temp_client': Mock(),
            'temp_phone': "+1234567890",
            'other_key': "value"
        }
        
        handler.cleanup_temp_handlers()
        
        assert 'temp_client' not in mock_tbot.handlers
        assert 'temp_phone' not in mock_tbot.handlers
        assert 'other_key' in mock_tbot.handlers
    
    async def test_update_groups(self, mock_tbot, mock_event, mock_telegram_client):
        """Test updating groups for all clients"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock(return_value=AsyncMock())
        mock_event.respond.return_value.edit = AsyncMock()
        
        mock_tbot.active_clients = {"session1": mock_telegram_client}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.config = {"clients": {"session1": []}}
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        
        mock_chat = Mock(spec=Chat)
        mock_chat.id = -1001234567890
        mock_chat.broadcast = False
        
        mock_dialog = Mock()
        mock_dialog.entity = mock_chat
        
        mock_telegram_client.iter_dialogs = AsyncMock(return_value=[mock_dialog])
        
        with patch('src.Client.CLIENTS_JSON_PATH', 'test_clients.json'):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = '{"clients": {}}'
                mock_file.__enter__.return_value = mock_file
                mock_open.return_value = mock_file
                
                await handler.update_groups(mock_event)
                
                mock_event.respond.assert_called()
    
    async def test_show_accounts(self, mock_tbot, mock_event):
        """Test showing all accounts"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.config = {
            "clients": {
                "session1": [123, 456],
                "session2": {"groups": [789], "is_reported": False}
            }
        }
        mock_tbot.active_clients = {"session1": Mock(), "session2": Mock()}
        mock_tbot.active_clients_lock = asyncio.Lock()
        
        await handler.show_accounts(mock_event)
        
        assert mock_event.respond.call_count >= 2  # At least one message per account
    
    async def test_toggle_client_enable(self, mock_tbot, mock_event, mock_telegram_client):
        """Test enabling a client"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.process_messages_for_client = AsyncMock()
        
        mock_telegram_client.is_user_authorized = AsyncMock(return_value=True)
        mock_telegram_client.is_connected = Mock(return_value=False)
        
        with patch('src.Client.get_safe_session_file_path', return_value="session1.session"):
            with patch('os.path.exists', return_value=True):
                with patch('src.Client.TelegramClient', return_value=mock_telegram_client):
                    await handler.toggle_client("session1", mock_event)
                    
                    assert "session1" in mock_tbot.active_clients
                    mock_event.respond.assert_called()
    
    async def test_toggle_client_disable(self, mock_tbot, mock_event, mock_telegram_client):
        """Test disabling a client"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {"session1": mock_telegram_client}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.cleanup_client_handlers = Mock()
        
        mock_telegram_client.disconnect = AsyncMock()
        
        await handler.toggle_client("session1", mock_event)
        
        assert "session1" not in mock_tbot.active_clients
        mock_event.respond.assert_called()
    
    async def test_delete_client(self, mock_tbot, mock_event, mock_telegram_client):
        """Test deleting a client"""
        handler = AccountHandler(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.config = {"clients": {"session1": []}}
        mock_tbot.active_clients = {"session1": mock_telegram_client}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.cleanup_client_handlers = Mock()
        
        mock_telegram_client.disconnect = AsyncMock()
        
        with patch('src.Client.get_safe_session_file_path', return_value="session1.session"):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    await handler.delete_client("session1", mock_event)
                    
                    assert "session1" not in mock_tbot.active_clients
                    assert "session1" not in mock_tbot.config["clients"]
                    mock_event.respond.assert_called()

