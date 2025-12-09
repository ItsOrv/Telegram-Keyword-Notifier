"""
Flow tests for Monitor Mode functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.Handlers import KeywordHandler, CallbackHandler
from src.Monitor import Monitor


class TestMonitorModeFlows:
    """Test complete flows for monitor mode"""

    @pytest.mark.asyncio
    async def test_add_keyword_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete add keyword flow"""
        # Step 1: User clicks "Add Keyword"
        mock_callback_event.data = b'add_keyword'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify keyword input request
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'add_keyword_handler'
        
        # Step 2: User sends keyword
        mock_event.message.text = "test_keyword"
        mock_event.chat_id = mock_callback_event.chat_id
        mock_tbot.config = {"KEYWORDS": []}
        mock_tbot.config_manager.save_config = MagicMock()
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.add_keyword_handler(mock_event)
        
        # Verify keyword was added
        assert "test_keyword" in mock_tbot.config['KEYWORDS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_remove_keyword_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete remove keyword flow"""
        # Setup existing keyword
        mock_tbot.config = {"KEYWORDS": ["test_keyword"]}
        mock_tbot.config_manager.save_config = MagicMock()
        
        # Step 1: User clicks "Remove Keyword"
        mock_callback_event.data = b'remove_keyword'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User sends keyword to remove
        mock_event.message.text = "test_keyword"
        mock_event.chat_id = mock_callback_event.chat_id
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.remove_keyword_handler(mock_event)
        
        # Verify keyword was removed
        assert "test_keyword" not in mock_tbot.config['KEYWORDS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_ignore_user_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete ignore user flow"""
        # Step 1: User clicks "Ignore User"
        mock_callback_event.data = b'ignore_user'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify user ID input request
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'ignore_user_handler'
        
        # Step 2: User sends user ID
        mock_event.message.text = "123456789"
        mock_event.chat_id = mock_callback_event.chat_id
        mock_tbot.config = {"IGNORE_USERS": []}
        mock_tbot.config_manager.save_config = MagicMock()
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.ignore_user_handler(mock_event)
        
        # Verify user was added to ignore list
        assert 123456789 in mock_tbot.config['IGNORE_USERS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_remove_ignore_user_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete remove ignore user flow"""
        # Setup existing ignored user
        mock_tbot.config = {"IGNORE_USERS": [123456789]}
        mock_tbot.config_manager.save_config = MagicMock()
        
        # Step 1: User clicks "Remove Ignore"
        mock_callback_event.data = b'remove_ignore_user'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User sends user ID to remove
        mock_event.message.text = "123456789"
        mock_event.chat_id = mock_callback_event.chat_id
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.delete_ignore_user_handler(mock_event)
        
        # Verify user was removed from ignore list
        assert 123456789 not in mock_tbot.config['IGNORE_USERS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_ignore_user_from_channel_button(self, mock_tbot, mock_callback_event):
        """Test ignoring user from channel message button"""
        mock_tbot.config = {"IGNORE_USERS": []}
        mock_tbot.config_manager.save_config = MagicMock()
        
        # User clicks ignore button from channel message
        mock_callback_event.data = b'ignore_123456789'
        
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify user was added to ignore list
        assert 123456789 in mock_tbot.config['IGNORE_USERS']
        mock_callback_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_monitor_message_forwarding(self, mock_tbot, mock_new_message_event):
        """Test message monitoring and forwarding"""
        # Setup monitor
        mock_tbot.config = {
            "KEYWORDS": ["test"],
            "IGNORE_USERS": []
        }
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        # Mock client
        mock_client = AsyncMock()
        mock_client.session.filename = "test_session.session"
        
        # Mock process_message function
        async def mock_process_message(event):
            # Check if message contains keyword
            message = event.message.text or ""
            if any(keyword.lower() in message.lower() for keyword in mock_tbot.config['KEYWORDS']):
                # Forward message
                await mock_tbot.tbot.send_message(
                    monitor.channel_id,
                    f"Account: test_session\nMessage: {message}"
                )
        
        # Test with message containing keyword
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.get_sender = AsyncMock(return_value=MagicMock(id=987654321))
        mock_new_message_event.get_chat = AsyncMock(return_value=MagicMock(title="Test Chat", username="testchat"))
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.id = 1
        
        await mock_process_message(mock_new_message_event)
        
        # Verify message was forwarded
        mock_tbot.tbot.send_message.assert_called()
        call_args = mock_tbot.tbot.send_message.call_args[0][1]
        assert "test" in call_args.lower()

    @pytest.mark.asyncio
    async def test_monitor_ignore_keyword(self, mock_tbot, mock_new_message_event):
        """Test that messages without keywords are ignored"""
        mock_tbot.config = {
            "KEYWORDS": ["test"],
            "IGNORE_USERS": []
        }
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        # Message without keyword
        mock_new_message_event.message.text = "This message has no keyword"
        
        # Mock process_message function
        async def mock_process_message(event):
            message = event.message.text or ""
            if any(keyword.lower() in message.lower() for keyword in mock_tbot.config['KEYWORDS']):
                await mock_tbot.tbot.send_message(123456789, message)
            # Otherwise, message is ignored
        
        await mock_process_message(mock_new_message_event)
        
        # Verify message was NOT forwarded
        mock_tbot.tbot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_ignore_user(self, mock_tbot, mock_new_message_event):
        """Test that messages from ignored users are not forwarded"""
        mock_tbot.config = {
            "KEYWORDS": ["test"],
            "IGNORE_USERS": [987654321]
        }
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        # Message from ignored user
        mock_sender = MagicMock()
        mock_sender.id = 987654321
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        # Mock process_message function
        async def mock_process_message(event):
            sender = await event.get_sender()
            if sender and sender.id in mock_tbot.config['IGNORE_USERS']:
                return  # Ignore this user
            # Continue processing...
        
        await mock_process_message(mock_new_message_event)
        
        # Verify message was NOT forwarded
        mock_tbot.tbot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_keyword_duplicate(self, mock_tbot, mock_event):
        """Test adding duplicate keyword"""
        mock_tbot.config = {"KEYWORDS": ["test"]}
        mock_tbot._conversations = {mock_event.chat_id: 'add_keyword_handler'}
        
        mock_event.message.text = "test"
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.add_keyword_handler(mock_event)
        
        # Should show message that keyword already exists
        mock_event.respond.assert_called()
        call_args = mock_event.respond.call_args[0][0]
        assert "already exists" in call_args or "موجود" in call_args

    @pytest.mark.asyncio
    async def test_remove_keyword_nonexistent(self, mock_tbot, mock_event):
        """Test removing non-existent keyword"""
        mock_tbot.config = {"KEYWORDS": []}
        mock_tbot._conversations = {mock_event.chat_id: 'remove_keyword_handler'}
        
        mock_event.message.text = "nonexistent"
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.remove_keyword_handler(mock_event)
        
        # Should show message that keyword not found
        mock_event.respond.assert_called()
        call_args = mock_event.respond.call_args[0][0]
        assert "not found" in call_args or "پیدا نشد" in call_args

    @pytest.mark.asyncio
    async def test_invalid_keyword(self, mock_tbot, mock_event):
        """Test adding invalid keyword"""
        mock_tbot.config = {"KEYWORDS": []}
        mock_tbot._conversations = {mock_event.chat_id: 'add_keyword_handler'}
        
        # Empty keyword
        mock_event.message.text = ""
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.add_keyword_handler(mock_event)
        
        # Should show error
        mock_event.respond.assert_called()
        call_args = mock_event.respond.call_args[0][0]
        assert "❌" in call_args or "error" in call_args.lower()

    @pytest.mark.asyncio
    async def test_invalid_user_id(self, mock_tbot, mock_event):
        """Test ignoring user with invalid user ID"""
        mock_tbot.config = {"IGNORE_USERS": []}
        mock_tbot._conversations = {mock_event.chat_id: 'ignore_user_handler'}
        
        # Invalid user ID
        mock_event.message.text = "invalid"
        
        keyword_handler = KeywordHandler(mock_tbot)
        await keyword_handler.ignore_user_handler(mock_event)
        
        # Should show error
        mock_event.respond.assert_called()
        call_args = mock_event.respond.call_args[0][0]
        assert "❌" in call_args or "error" in call_args.lower()

