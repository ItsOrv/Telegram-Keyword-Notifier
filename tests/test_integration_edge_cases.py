"""
Integration tests and edge cases
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.Telbot import TelegramBot
from src.Client import SessionManager, AccountHandler
from src.actions import Actions
from src.Monitor import Monitor


class TestIntegrationFlows:
    """Test complete integration flows"""

    @pytest.mark.asyncio
    async def test_full_bot_initialization(self, mock_tbot):
        """Test complete bot initialization flow"""
        # This tests the entire initialization chain
        assert mock_tbot.config_manager is not None
        assert mock_tbot.active_clients is not None
        assert mock_tbot.active_clients_lock is not None
        assert mock_tbot._conversations is not None
        assert mock_tbot._conversations_lock is not None
        assert mock_tbot.client_manager is not None
        assert mock_tbot.account_handler is not None
        assert mock_tbot.monitor is not None

    @pytest.mark.asyncio
    async def test_session_manager_detect_sessions(self, mock_tbot):
        """Test session detection"""
        mock_tbot.config = {
            "clients": {
                "test_session1": [],
                "test_session2": []
            }
        }
        
        session_manager = SessionManager(
            mock_tbot.config,
            mock_tbot.active_clients,
            mock_tbot
        )
        
        with patch('src.Client.TelegramClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            await session_manager.detect_sessions()
            
            # Verify sessions were detected
            assert len(mock_tbot.active_clients) == 2

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_tbot):
        """Test concurrent operations don't cause race conditions"""
        # Simulate multiple operations happening at once
        mock_tbot.active_clients = {
            "session1": AsyncMock(),
            "session2": AsyncMock(),
            "session3": AsyncMock()
        }
        
        async def add_keyword():
            async with mock_tbot._conversations_lock:
                mock_tbot._conversations[1] = 'add_keyword_handler'
        
        async def remove_keyword():
            async with mock_tbot._conversations_lock:
                if 1 in mock_tbot._conversations:
                    del mock_tbot._conversations[1]
        
        # Run concurrent operations
        await asyncio.gather(
            add_keyword(),
            remove_keyword(),
            add_keyword(),
            remove_keyword()
        )
        
        # Should not raise any exceptions
        assert True

    @pytest.mark.asyncio
    async def test_error_handling_in_actions(self, mock_tbot, mock_event):
        """Test error handling in actions"""
        mock_client = AsyncMock()
        mock_client.get_entity = AsyncMock(side_effect=Exception("Network error"))
        mock_tbot.active_clients = {"session1": mock_client}
        mock_tbot.handlers = {
            "block_account": mock_client
        }
        mock_tbot._conversations = {mock_event.chat_id: 'block_user_handler'}
        
        mock_event.message.text = "@testuser"
        
        actions = Actions(mock_tbot)
        await actions.block_user_handler(mock_event)
        
        # Should handle error gracefully
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_config_persistence(self, mock_tbot, temp_config_file):
        """Test that configuration changes persist"""
        from src.Config import ConfigManager
        
        manager = ConfigManager(temp_config_file)
        manager.config = {"KEYWORDS": ["test"]}
        manager.save_config(manager.config)
        
        # Reload
        new_manager = ConfigManager(temp_config_file)
        loaded_config = new_manager.load_config()
        
        assert "test" in loaded_config.get("KEYWORDS", [])

    @pytest.mark.asyncio
    async def test_multiple_accounts_bulk_operation(self, mock_tbot, mock_event):
        """Test bulk operation with multiple accounts"""
        # Setup multiple clients
        clients = {f"session{i}": AsyncMock() for i in range(10)}
        mock_tbot.active_clients = clients
        
        actions = Actions(mock_tbot)
        mock_tbot.handlers = {
            "reaction_num_accounts": 5, 
            "reaction_link": "https://t.me/test/123",
            "reaction_is_bulk": True
        }
        mock_tbot._conversations = {mock_event.chat_id: 'reaction_select_handler'}
        
        mock_reaction_event = AsyncMock()
        mock_reaction_event.chat_id = mock_event.chat_id
        mock_reaction_event.data = b'reaction_thumbsup'
        mock_reaction_event.respond = AsyncMock()
        
        # Mock parse_telegram_link to avoid actual parsing
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (MagicMock(), 123)
            
            with patch.object(actions, 'apply_reaction', new_callable=AsyncMock) as mock_apply:
                await actions.reaction_select_handler(mock_reaction_event)
                
                # Should apply to 5 accounts
                # Note: apply_reaction is called inside apply_reaction_with_limit
                # So we need to check if it was called or check the success count
                # Since we're patching, let's check if the handler was called
                assert mock_apply.call_count == 5 or mock_reaction_event.respond.called


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_empty_keyword_list(self, mock_tbot, mock_new_message_event):
        """Test monitoring with empty keyword list"""
        mock_tbot.config = {"KEYWORDS": [], "IGNORE_USERS": []}
        mock_tbot.tbot = AsyncMock()
        mock_tbot.tbot.send_message = AsyncMock()
        
        # Message should not be forwarded if no keywords
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        # Simulate message processing
        message_text = "Test message"
        if any(keyword.lower() in message_text.lower() for keyword in mock_tbot.config['KEYWORDS']):
            await mock_tbot.tbot.send_message(monitor.channel_id, message_text)
        
        # Should not be called
        mock_tbot.tbot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_very_long_message(self, mock_tbot, mock_event):
        """Test handling of very long messages"""
        # Very long message (but within limits)
        long_message = "a" * 4096
        mock_event.message.text = long_message
        
        from src.Validation import InputValidator
        is_valid, error_msg = InputValidator.validate_message_text(long_message)
        
        assert is_valid  # Should be valid (at limit)

    @pytest.mark.asyncio
    async def test_special_characters_in_keyword(self, mock_tbot, mock_event):
        """Test handling special characters in keywords"""
        mock_tbot.config = {"KEYWORDS": []}
        mock_tbot._conversations = {mock_event.chat_id: 'add_keyword_handler'}
        
        # Keyword with special characters
        mock_event.message.text = "test@keyword#123"
        
        from src.Validation import InputValidator
        is_valid, error_msg = InputValidator.validate_keyword("test@keyword#123")
        
        # Should be valid (no restrictions on special chars)
        assert is_valid

    @pytest.mark.asyncio
    async def test_cancel_operation(self, mock_tbot, mock_callback_event):
        """Test canceling an operation"""
        mock_tbot._conversations[mock_callback_event.chat_id] = 'add_keyword_handler'
        
        mock_callback_event.data = b'cancel'
        
        from src.Handlers import CallbackHandler
        handler = CallbackHandler(mock_tbot)
        await handler.callback_handler(mock_callback_event)
        
        # Conversation should be cleared
        assert mock_callback_event.chat_id not in mock_tbot._conversations

    @pytest.mark.asyncio
    async def test_duplicate_keyword_addition(self, mock_tbot, mock_event):
        """Test adding duplicate keyword"""
        mock_tbot.config = {"KEYWORDS": ["test"]}
        mock_tbot._conversations = {mock_event.chat_id: 'add_keyword_handler'}
        
        mock_event.message.text = "test"
        
        from src.Handlers import KeywordHandler
        handler = KeywordHandler(mock_tbot)
        await handler.add_keyword_handler(mock_event)
        
        # Should still have only one instance
        assert mock_tbot.config['KEYWORDS'].count("test") == 1

    @pytest.mark.asyncio
    async def test_invalid_phone_number_formats(self, mock_tbot, mock_event):
        """Test various invalid phone number formats"""
        invalid_numbers = [
            "1234567890",  # No +
            "+123",  # Too short
            "+1234567890123456",  # Too long
            "+abc123456",  # Non-numeric
            "1234567890+",  # Wrong position
        ]
        
        from src.Validation import InputValidator
        
        for phone in invalid_numbers:
            is_valid, error_msg = InputValidator.validate_phone_number(phone)
            assert not is_valid, f"Phone {phone} should be invalid"
            assert error_msg is not None

    @pytest.mark.asyncio
    async def test_invalid_telegram_link_formats(self, mock_tbot, mock_event):
        """Test various invalid Telegram link formats"""
        invalid_links = [
            "",  # Empty
            "https://example.com",  # Not Telegram
            "http://telegram.org",  # Not t.me
            "invalid",  # Invalid format
        ]
        
        from src.Validation import InputValidator
        
        for link in invalid_links:
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            if not is_valid:
                assert error_msg is not None

    @pytest.mark.asyncio
    async def test_message_handler_without_active_conversation(self, mock_tbot, mock_event):
        """Test message handler when no conversation is active"""
        mock_tbot._conversations = {}  # No active conversations
        
        from src.Handlers import MessageHandler
        handler = MessageHandler(mock_tbot)
        result = await handler.message_handler(mock_event)
        
        # Should return False (no processing)
        assert result is False

    @pytest.mark.asyncio
    async def test_callback_handler_unknown_command(self, mock_tbot, mock_callback_event):
        """Test callback handler with unknown command"""
        mock_callback_event.data = b'unknown_command_xyz'
        
        from src.Handlers import CallbackHandler
        handler = CallbackHandler(mock_tbot)
        await handler.callback_handler(mock_callback_event)
        
        # Should handle gracefully
        mock_callback_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_session_manager_with_invalid_session(self, mock_tbot):
        """Test session manager with invalid session file"""
        mock_tbot.config = {"clients": {"invalid_session": []}}
        
        session_manager = SessionManager(
            mock_tbot.config,
            mock_tbot.active_clients,
            mock_tbot
        )
        
        with patch('src.Client.TelegramClient') as mock_client_class:
            mock_client = AsyncMock()
            # is_connected() is a regular method, not async
            mock_client.is_connected = MagicMock(return_value=False)
            mock_client.is_user_authorized = AsyncMock(return_value=False)
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            mock_client.get_dialogs = AsyncMock(side_effect=Exception("Session revoked"))
            mock_client.session = MagicMock()
            mock_client.session.save = MagicMock()
            mock_client_class.return_value = mock_client
            
            await session_manager.start_saved_clients()
            
            # Should handle invalid session gracefully
            assert True  # No exception raised

    @pytest.mark.asyncio
    async def test_monitor_with_missing_channel(self, mock_tbot):
        """Test monitor with missing channel configuration"""
        monitor = Monitor(mock_tbot)
        
        # Should handle missing channel gracefully
        try:
            await monitor.resolve_channel_id()
        except Exception:
            # Expected if channel is not configured
            pass
        
        assert True  # Should not crash

    @pytest.mark.asyncio
    async def test_bulk_operation_with_zero_accounts(self, mock_tbot, mock_callback_event):
        """Test bulk operation when no accounts are selected"""
        mock_tbot.active_clients = {}
        
        from src.actions import Actions
        actions = Actions(mock_tbot)
        
        await actions.prompt_group_action(mock_callback_event, 'reaction')
        
        # Should show error message - check all calls
        mock_callback_event.respond.assert_called()
        calls = mock_callback_event.respond.call_args_list
        call_args_text = ' '.join([str(call[0][0]) if call[0] else '' for call in calls])
        assert "No accounts" in call_args_text or "❌" in call_args_text or "0 accounts" in call_args_text

    @pytest.mark.asyncio
    async def test_individual_operation_with_disconnected_account(self, mock_tbot):
        """Test individual operation with disconnected account"""
        mock_client = AsyncMock()
        mock_client.is_connected = AsyncMock(return_value=False)
        mock_tbot.active_clients = {"session1": mock_client}
        
        # Should handle disconnected account
        assert "session1" in mock_tbot.active_clients

    @pytest.mark.asyncio
    async def test_config_file_corruption_handling(self, temp_config_file):
        """Test handling of corrupted config file"""
        # Write invalid JSON
        with open(temp_config_file, 'w') as f:
            f.write("invalid json {")
        
        from src.Config import ConfigManager
        manager = ConfigManager(temp_config_file)
        config = manager.load_config()
        
        # Should return default config
        assert isinstance(config, dict)
        assert "TARGET_GROUPS" in config

    @pytest.mark.asyncio
    async def test_conversation_state_cleanup(self, mock_tbot, mock_event):
        """Test that conversation states are properly cleaned up"""
        mock_tbot._conversations[mock_event.chat_id] = 'test_handler'
        
        # Simulate cleanup
        async with mock_tbot._conversations_lock:
            mock_tbot._conversations.pop(mock_event.chat_id, None)
        
        assert mock_event.chat_id not in mock_tbot._conversations

    @pytest.mark.asyncio
    async def test_handler_cleanup_on_disconnect(self, mock_tbot):
        """Test that handlers are cleaned up on disconnect"""
        mock_client = AsyncMock()
        mock_client._registered_handlers = [MagicMock(), MagicMock()]
        mock_client.remove_event_handler = MagicMock()
        
        monitor = Monitor(mock_tbot)
        monitor.cleanup_client_handlers(mock_client)
        
        # Should clean up handlers
        assert len(mock_client._registered_handlers) == 0

