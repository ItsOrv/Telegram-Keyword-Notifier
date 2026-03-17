"""
Comprehensive tests for utils.py module
Tests all utility functions with edge cases and error scenarios
"""
import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telethon.errors import FloodWaitError, SessionRevokedError
from telethon import TelegramClient

try:
    from telethon.errors.rpcerrorlist import AuthKeyUnregisteredError
except ImportError:
    AuthKeyUnregisteredError = None

from src.utils import (
    sanitize_session_name,
    get_safe_session_file_path,
    get_session_name,
    cleanup_conversation_state,
    is_session_revoked_error,
    validate_admin_id,
    check_admin_access,
    execute_bulk_operation,
    format_bulk_result_message,
    get_bot_user_id,
    is_bot_message,
    cleanup_handlers_and_state,
    resolve_entity,
    send_error_message,
    extract_account_name,
    prompt_for_input,
    validate_and_respond,
    check_account_exists,
    remove_revoked_session_completely,
    check_accounts_available
)


class TestSanitizeSessionName:
    """Comprehensive tests for sanitize_session_name"""
    
    def test_valid_session_names(self):
        """Test valid session names"""
        valid_names = [
            "test_session",
            "session123",
            "test-session",
            "test_session_123",
            "a" * 255,  # Max length
            "1234567890",
            "+1234567890"
        ]
        for name in valid_names:
            result = sanitize_session_name(name)
            assert result is not None
            assert len(result) > 0
    
    def test_invalid_session_names(self):
        """Test invalid session names"""
        invalid_cases = [
            ("", ValueError),
            (None, ValueError),
        ]
        for name, expected_error in invalid_cases:
            with pytest.raises(expected_error):
                sanitize_session_name(name)
    
    def test_empty_after_sanitization(self):
        """Test names that become empty after sanitization"""
        invalid_cases = [
            "   ",
            "...",
            "---",
            "___",
        ]
        for name in invalid_cases:
            with pytest.raises(ValueError):
                sanitize_session_name(name)
    
    def test_path_traversal_attempts(self):
        """Test path traversal attack prevention"""
        # sanitize_session_name removes path separators and '..'
        # Some attacks become empty, others become valid names (which is safe)
        attack_attempts_that_become_empty = [
            "../../",  # Becomes empty
            "..\\..\\",  # Becomes empty
        ]
        for attack in attack_attempts_that_become_empty:
            with pytest.raises(ValueError):
                sanitize_session_name(attack)
        
        # These attacks become safe names after sanitization (path separators removed)
        attack_attempts_that_become_safe = [
            "../../etc/passwd",  # Becomes "etcpasswd" (safe)
            "..\\..\\windows\\system32",  # Becomes "windowssystem32" (safe)
        ]
        for attack in attack_attempts_that_become_safe:
            result = sanitize_session_name(attack)
            # Should not contain path separators
            assert "/" not in result
            assert "\\" not in result
            assert ".." not in result
            assert len(result) > 0
    
    def test_special_characters_removal(self):
        """Test removal of special characters"""
        test_cases = [
            ("test@session", "testsession"),
            ("test#session", "testsession"),
            ("test$session", "testsession"),
            ("test session", "testsession"),
            ("test\nsession", "testsession"),
        ]
        for input_name, expected_pattern in test_cases:
            result = sanitize_session_name(input_name)
            # Should not contain special chars
            assert "@" not in result
            assert "#" not in result
            assert "$" not in result
            assert " " not in result
            assert "\n" not in result
    
    def test_length_truncation(self):
        """Test session name length truncation"""
        long_name = "a" * 500
        result = sanitize_session_name(long_name)
        assert len(result) <= 255
    
    def test_leading_trailing_dots_removal(self):
        """Test removal of leading/trailing dots and dashes"""
        test_cases = [
            (".test.", "test"),
            ("-test-", "test"),
            ("_test_", "test"),
            ("...test...", "test"),
        ]
        for input_name, expected in test_cases:
            result = sanitize_session_name(input_name)
            assert not result.startswith(('.', '-', '_'))
            assert not result.endswith(('.', '-', '_'))


class TestGetSafeSessionFilePath:
    """Comprehensive tests for get_safe_session_file_path"""
    
    def test_valid_paths(self):
        """Test valid session file paths"""
        valid_names = ["test_session", "session123", "+1234567890"]
        for name in valid_names:
            result = get_safe_session_file_path(name)
            assert result.endswith(".session")
            assert os.path.basename(result) == f"{sanitize_session_name(name)}.session"
    
    def test_path_traversal_prevention(self):
        """Test path traversal prevention"""
        attack_attempts = [
            "../../etc/passwd",
            "..\\..\\config",
            "/etc/passwd",
        ]
        for attack in attack_attempts:
            with pytest.raises(ValueError):
                get_safe_session_file_path(attack)
    
    def test_custom_project_dir(self):
        """Test with custom project directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = get_safe_session_file_path("test_session", temp_dir)
            assert result.startswith(temp_dir)
            assert os.path.basename(result) == "test_session.session"
    
    def test_absolute_path_verification(self):
        """Test that final path is within project directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Even with sanitization, path should stay within project dir
            result = get_safe_session_file_path("test", temp_dir)
            assert os.path.abspath(result).startswith(os.path.abspath(temp_dir))


class TestGetSessionName:
    """Comprehensive tests for get_session_name"""
    
    def test_valid_client(self):
        """Test with valid client"""
        mock_client = Mock()
        mock_client.session = Mock()
        mock_client.session.filename = "test.session"
        result = get_session_name(mock_client)
        assert result == "test.session"
    
    def test_client_without_session(self):
        """Test with client without session"""
        mock_client = Mock()
        del mock_client.session
        result = get_session_name(mock_client)
        assert result == "Unknown"
    
    def test_client_without_filename(self):
        """Test with client without filename"""
        mock_client = Mock()
        mock_client.session = Mock()
        mock_client.session.filename = None
        result = get_session_name(mock_client)
        assert result == "Unknown"
    
    def test_exception_handling(self):
        """Test exception handling"""
        mock_client = Mock()
        mock_client.session = Mock()
        mock_client.session.filename = Mock(side_effect=Exception("Error"))
        result = get_session_name(mock_client)
        assert result == "Unknown"


class TestIsSessionRevokedError:
    """Comprehensive tests for is_session_revoked_error"""
    
    def test_session_revoked_error(self):
        """Test SessionRevokedError"""
        error = SessionRevokedError()
        assert is_session_revoked_error(error) is True
    
    def test_auth_key_unregistered_error(self):
        """Test AuthKeyUnregisteredError"""
        if AuthKeyUnregisteredError:
            error = AuthKeyUnregisteredError()
            assert is_session_revoked_error(error) is True
    
    def test_error_messages(self):
        """Test error message detection"""
        error_messages = [
            "Session revoked",
            "session not logged in",
            "auth key is not registered",
            "invalid session",
            "unregistered auth key"
        ]
        for msg in error_messages:
            error = Exception(msg)
            assert is_session_revoked_error(error) is True
    
    def test_error_type_names(self):
        """Test error type name detection"""
        class SessionRevoked(Exception):
            pass
        
        class AuthError(Exception):
            pass
        
        error1 = SessionRevoked("test")
        error2 = AuthError("test")
        
        assert is_session_revoked_error(error1) is True
        assert is_session_revoked_error(error2) is True
    
    def test_non_revoked_errors(self):
        """Test non-revoked errors"""
        non_revoked = [
            Exception("Network error"),
            ValueError("Invalid input"),
            KeyError("key"),
            FloodWaitError(seconds=60)
        ]
        for error in non_revoked:
            if not isinstance(error, FloodWaitError):
                assert is_session_revoked_error(error) is False


class TestValidateAdminId:
    """Comprehensive tests for validate_admin_id"""
    
    def test_valid_admin_ids(self):
        """Test valid admin IDs"""
        valid_ids = [1, 123456789, "123456789", "1"]
        for admin_id in valid_ids:
            result = validate_admin_id(admin_id)
            assert isinstance(result, int)
            assert result > 0
    
    def test_invalid_admin_ids(self):
        """Test invalid admin IDs"""
        invalid_cases = [
            (None, ValueError),
            (0, ValueError),
            (-1, ValueError),
            ("0", ValueError),
            ("-1", ValueError),
            ("abc", ValueError),
            ("", ValueError),
        ]
        for admin_id, expected_error in invalid_cases:
            with pytest.raises(expected_error):
                validate_admin_id(admin_id)


@pytest.mark.asyncio
class TestCheckAdminAccess:
    """Comprehensive tests for check_admin_access"""
    
    async def test_admin_access(self):
        """Test admin access granted"""
        mock_event = Mock()
        mock_event.sender_id = 123456789
        admin_id = 123456789
        result = await check_admin_access(mock_event, admin_id)
        assert result is True
    
    async def test_non_admin_access(self):
        """Test non-admin access denied"""
        mock_event = Mock()
        mock_event.sender_id = 999999999
        admin_id = 123456789
        result = await check_admin_access(mock_event, admin_id)
        assert result is False
    
    async def test_test_mode(self):
        """Test test mode (admin_id = 0)"""
        mock_event = Mock()
        mock_event.sender_id = 999999999
        admin_id = 0  # Test mode
        result = await check_admin_access(mock_event, admin_id)
        assert result is True
    
    async def test_invalid_admin_id(self):
        """Test with invalid admin_id"""
        mock_event = Mock()
        mock_event.sender_id = 123456789
        admin_id = None
        result = await check_admin_access(mock_event, admin_id)
        assert result is False


@pytest.mark.asyncio
class TestExecuteBulkOperation:
    """Comprehensive tests for execute_bulk_operation"""
    
    async def test_successful_operations(self):
        """Test successful bulk operations"""
        accounts = [Mock(), Mock(), Mock()]
        operation = AsyncMock()
        semaphore = asyncio.Semaphore(3)
        counter_lock = asyncio.Lock()
        
        success, errors, revoked = await execute_bulk_operation(
            accounts, operation, "test_operation", semaphore, counter_lock
        )
        
        assert success == 3
        assert errors == 0
        assert len(revoked) == 0
        assert operation.call_count == 3
    
    async def test_flood_wait_error(self):
        """Test FloodWaitError handling"""
        accounts = [Mock(), Mock()]
        operation = AsyncMock(side_effect=FloodWaitError(seconds=1))
        semaphore = asyncio.Semaphore(3)
        counter_lock = asyncio.Lock()
        
        success, errors, revoked = await execute_bulk_operation(
            accounts, operation, "test_operation", semaphore, counter_lock, (0.1, 0.2)
        )
        
        assert success == 0
        assert errors == 2
        assert len(revoked) == 0
    
    async def test_session_revoked_error(self):
        """Test SessionRevokedError handling"""
        accounts = [Mock(), Mock()]
        accounts[0].session = Mock()
        accounts[0].session.filename = "session1.session"
        accounts[1].session = Mock()
        accounts[1].session.filename = "session2.session"
        
        operation = AsyncMock(side_effect=SessionRevokedError())
        semaphore = asyncio.Semaphore(3)
        counter_lock = asyncio.Lock()
        
        success, errors, revoked = await execute_bulk_operation(
            accounts, operation, "test_operation", semaphore, counter_lock
        )
        
        assert success == 0
        assert errors == 2
        assert len(revoked) == 2
    
    async def test_mixed_results(self):
        """Test mixed success and error results"""
        accounts = [Mock(), Mock(), Mock()]
        accounts[0].session = Mock()
        accounts[0].session.filename = "session1.session"
        accounts[1].session = Mock()
        accounts[1].session.filename = "session2.session"
        accounts[2].session = Mock()
        accounts[2].session.filename = "session3.session"
        
        def operation_side_effect(acc):
            if acc == accounts[0]:
                return AsyncMock()()
            elif acc == accounts[1]:
                raise SessionRevokedError()
            else:
                raise Exception("Other error")
        
        operation = AsyncMock(side_effect=operation_side_effect)
        semaphore = asyncio.Semaphore(3)
        counter_lock = asyncio.Lock()
        
        success, errors, revoked = await execute_bulk_operation(
            accounts, operation, "test_operation", semaphore, counter_lock, (0.1, 0.2)
        )
        
        assert success == 1
        assert errors == 2
        assert len(revoked) == 1


@pytest.mark.asyncio
class TestFormatBulkResultMessage:
    """Comprehensive tests for format_bulk_result_message"""
    
    async def test_all_success(self):
        """Test message when all operations succeed"""
        result = await format_bulk_result_message(
            "Test Operation", 5, 0, []
        )
        assert "completed successfully" in result.lower()
        assert "5" in result
    
    async def test_with_errors(self):
        """Test message with errors"""
        result = await format_bulk_result_message(
            "Test Operation", 3, 2, []
        )
        assert "3" in result
        assert "2" in result
        assert "error" in result.lower()
    
    async def test_with_revoked_sessions(self):
        """Test message with revoked sessions"""
        result = await format_bulk_result_message(
            "Test Operation", 2, 1, ["session1", "session2"]
        )
        assert "2" in result
        assert "revoked" in result.lower()
        assert "2 account(s) were revoked" in result


class TestGetBotUserId:
    """Comprehensive tests for get_bot_user_id"""
    
    def test_valid_bot_token(self):
        """Test valid bot token"""
        token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        result = get_bot_user_id(token)
        assert result == 123456789
    
    def test_invalid_bot_token(self):
        """Test invalid bot token"""
        invalid_tokens = [
            "",
            "invalid",
            ":token",
            "token:",
            None
        ]
        for token in invalid_tokens:
            result = get_bot_user_id(token)
            assert result is None


class TestIsBotMessage:
    """Comprehensive tests for is_bot_message"""
    
    def test_bot_message(self):
        """Test bot message detection"""
        mock_event = Mock()
        mock_event.sender_id = 123456789
        bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        result = is_bot_message(mock_event, bot_token)
        assert result is True
    
    def test_non_bot_message(self):
        """Test non-bot message"""
        mock_event = Mock()
        mock_event.sender_id = 999999999
        bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        result = is_bot_message(mock_event, bot_token)
        assert result is False
    
    def test_invalid_bot_token(self):
        """Test with invalid bot token"""
        mock_event = Mock()
        mock_event.sender_id = 123456789
        bot_token = "invalid"
        result = is_bot_message(mock_event, bot_token)
        assert result is False


@pytest.mark.asyncio
class TestCleanupHandlersAndState:
    """Comprehensive tests for cleanup_handlers_and_state"""
    
    async def test_cleanup_handlers(self):
        """Test handler cleanup"""
        mock_tbot = Mock()
        mock_tbot.handlers = {"key1": "value1", "key2": "value2"}
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        
        await cleanup_handlers_and_state(mock_tbot, ["key1", "key2"])
        
        assert "key1" not in mock_tbot.handlers
        assert "key2" not in mock_tbot.handlers
    
    async def test_cleanup_with_chat_id(self):
        """Test cleanup with chat_id"""
        mock_tbot = Mock()
        mock_tbot.handlers = {"key1": "value1"}
        mock_tbot._conversations = {123: "state1"}
        mock_tbot._conversations_lock = asyncio.Lock()
        
        await cleanup_handlers_and_state(mock_tbot, ["key1"], chat_id=123)
        
        assert "key1" not in mock_tbot.handlers
        assert 123 not in mock_tbot._conversations


@pytest.mark.asyncio
class TestResolveEntity:
    """Comprehensive tests for resolve_entity"""
    
    async def test_resolve_string_username(self):
        """Test resolving string username"""
        mock_account = AsyncMock()
        mock_entity = Mock()
        mock_account.get_entity = AsyncMock(return_value=mock_entity)
        
        result = await resolve_entity("username", mock_account)
        assert result == mock_entity
        mock_account.get_entity.assert_called_once_with("username")
    
    async def test_resolve_int_id(self):
        """Test resolving integer ID"""
        mock_account = AsyncMock()
        mock_entity = Mock()
        mock_account.get_entity = AsyncMock(return_value=mock_entity)
        
        result = await resolve_entity(-1001234567890, mock_account)
        assert result == mock_entity
    
    async def test_resolve_already_resolved(self):
        """Test with already resolved entity"""
        mock_entity = Mock()
        mock_account = Mock()
        
        result = await resolve_entity(mock_entity, mock_account)
        assert result == mock_entity
    
    async def test_resolve_none(self):
        """Test resolving None"""
        mock_account = Mock()
        with pytest.raises(ValueError):
            await resolve_entity(None, mock_account)
    
    async def test_resolve_empty_string(self):
        """Test resolving empty string"""
        mock_account = Mock()
        with pytest.raises(ValueError):
            await resolve_entity("", mock_account)
    
    async def test_session_revoked_during_resolve(self):
        """Test session revoked error during resolve"""
        mock_account = AsyncMock()
        mock_account.get_entity = AsyncMock(side_effect=SessionRevokedError())
        
        with pytest.raises(SessionRevokedError):
            await resolve_entity("username", mock_account)


@pytest.mark.asyncio
class TestSendErrorMessage:
    """Comprehensive tests for send_error_message"""
    
    async def test_code_error(self):
        """Test code error message"""
        mock_tbot = Mock()
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        error = Exception("phone code invalid")
        await send_error_message(mock_tbot, 123, error, "code")
        
        mock_tbot.tbot.send_message.assert_called_once()
        call_args = mock_tbot.tbot.send_message.call_args
        assert "invalid verification code" in call_args[0][1].lower()
    
    async def test_password_error(self):
        """Test password error message"""
        mock_tbot = Mock()
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        error = Exception("invalid password")
        await send_error_message(mock_tbot, 123, error, "password")
        
        mock_tbot.tbot.send_message.assert_called_once()
    
    async def test_phone_error(self):
        """Test phone error message"""
        mock_tbot = Mock()
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        error = Exception("flood wait")
        await send_error_message(mock_tbot, 123, error, "phone")
        
        mock_tbot.tbot.send_message.assert_called_once()
    
    async def test_general_error(self):
        """Test general error message"""
        mock_tbot = Mock()
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        error = Exception("unknown error")
        await send_error_message(mock_tbot, 123, error, "general")
        
        mock_tbot.tbot.send_message.assert_called_once()


class TestExtractAccountName:
    """Comprehensive tests for extract_account_name"""
    
    def test_valid_client(self):
        """Test with valid client"""
        mock_client = Mock()
        mock_client.session = Mock()
        mock_client.session.filename = "test.session"
        result = extract_account_name(mock_client)
        assert result == "test"
    
    def test_client_without_session(self):
        """Test with client without session"""
        mock_client = Mock()
        del mock_client.session
        result = extract_account_name(mock_client)
        assert result == "Unknown Account"
    
    def test_client_without_filename(self):
        """Test with client without filename"""
        mock_client = Mock()
        mock_client.session = Mock()
        mock_client.session.filename = None
        result = extract_account_name(mock_client)
        assert result == "Unknown Account"
    
    def test_exception_handling(self):
        """Test exception handling"""
        mock_client = Mock()
        mock_client.session = Mock()
        mock_client.session.filename = Mock(side_effect=Exception("Error"))
        result = extract_account_name(mock_client)
        assert result == "Unknown Account"


@pytest.mark.asyncio
class TestPromptForInput:
    """Comprehensive tests for prompt_for_input"""
    
    async def test_with_cancel_button(self):
        """Test prompt with cancel button"""
        mock_tbot = Mock()
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        
        await prompt_for_input(
            mock_tbot, mock_event,
            "Enter value:", "test_state", cancel_button=True
        )
        
        mock_event.respond.assert_called_once()
        assert mock_tbot._conversations[mock_event.chat_id] == "test_state"
    
    async def test_without_cancel_button(self):
        """Test prompt without cancel button"""
        mock_tbot = Mock()
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        
        await prompt_for_input(
            mock_tbot, mock_event,
            "Enter value:", "test_state", cancel_button=False
        )
        
        mock_event.respond.assert_called_once()


@pytest.mark.asyncio
class TestValidateAndRespond:
    """Comprehensive tests for validate_and_respond"""
    
    async def test_valid_input(self):
        """Test valid input"""
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        
        def validation_func(value):
            return (True, None, value.upper())
        
        is_valid, result = await validate_and_respond(
            mock_event, validation_func, "test", ""
        )
        
        assert is_valid is True
        assert result == "TEST"
        mock_event.respond.assert_not_called()
    
    async def test_invalid_input(self):
        """Test invalid input"""
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        
        def validation_func(value):
            return (False, "Invalid input", None)
        
        is_valid, result = await validate_and_respond(
            mock_event, validation_func, "invalid", "Error: "
        )
        
        assert is_valid is False
        assert result is None
        mock_event.respond.assert_called_once()


@pytest.mark.asyncio
class TestCheckAccountExists:
    """Comprehensive tests for check_account_exists"""
    
    async def test_account_exists(self):
        """Test when account exists"""
        mock_tbot = Mock()
        mock_tbot.handlers = {"account": Mock()}
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        
        exists, account = await check_account_exists(mock_tbot, mock_event)
        
        assert exists is True
        assert account is not None
        mock_event.respond.assert_not_called()
    
    async def test_account_not_exists(self):
        """Test when account doesn't exist"""
        mock_tbot = Mock()
        mock_tbot.handlers = {}
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        mock_event.chat_id = 123
        
        exists, account = await check_account_exists(mock_tbot, mock_event)
        
        assert exists is False
        assert account is None
        mock_event.respond.assert_called_once()


@pytest.mark.asyncio
class TestCheckAccountsAvailable:
    """Comprehensive tests for check_accounts_available"""
    
    async def test_accounts_available(self):
        """Test when accounts are available"""
        mock_tbot = Mock()
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        
        accounts = [Mock(), Mock()]
        result = await check_accounts_available(mock_tbot, mock_event, accounts)
        
        assert result is True
        mock_event.respond.assert_not_called()
    
    async def test_no_accounts_available(self):
        """Test when no accounts available"""
        mock_tbot = Mock()
        mock_tbot._conversations = {}
        mock_tbot._conversations_lock = asyncio.Lock()
        mock_event = AsyncMock()
        mock_event.respond = AsyncMock()
        mock_event.chat_id = 123
        
        accounts = []
        result = await check_accounts_available(mock_tbot, mock_event, accounts)
        
        assert result is False
        mock_event.respond.assert_called_once()


@pytest.mark.asyncio
class TestRemoveRevokedSessionCompletely:
    """Comprehensive tests for remove_revoked_session_completely"""
    
    async def test_remove_from_all_locations(self):
        """Test removing session from all locations"""
        mock_tbot = Mock()
        mock_tbot.active_clients = {"session1": Mock()}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.config = {"clients": {"session1": []}}
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        mock_tbot.monitor = Mock()
        mock_tbot.monitor.cleanup_client_handlers = Mock()
        
        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_tbot.active_clients["session1"] = mock_client
        
        with patch('src.utils.get_safe_session_file_path', return_value="session1.session"):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove') as mock_remove:
                    await remove_revoked_session_completely(mock_tbot, "session1")
                    
                    assert "session1" not in mock_tbot.active_clients
                    assert "session1" not in mock_tbot.config["clients"]
                    mock_client.disconnect.assert_called_once()
                    mock_remove.assert_called_once()
    
    async def test_remove_from_inactive_accounts(self):
        """Test removing from inactive_accounts"""
        mock_tbot = Mock()
        mock_tbot.active_clients = {}
        mock_tbot.active_clients_lock = asyncio.Lock()
        mock_tbot.config = {
            "clients": {},
            "inactive_accounts": {"session1": {}}
        }
        mock_tbot.config_manager = Mock()
        mock_tbot.config_manager.save_config = Mock()
        
        with patch('src.utils.get_safe_session_file_path', return_value="session1.session"):
            await remove_revoked_session_completely(mock_tbot, "session1")
            
            assert "session1" not in mock_tbot.config.get("inactive_accounts", {})

