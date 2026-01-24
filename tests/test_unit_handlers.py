"""
Unit tests for Handler classes
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.Handlers import CommandHandler, MessageHandler, CallbackHandler, KeywordHandler, StatsHandler


class TestCommandHandler:
    """Test suite for CommandHandler"""

    @pytest.mark.asyncio
    async def test_start_command_admin(self, mock_tbot, mock_admin_event):
        """Test /start command from admin"""
        handler = CommandHandler(mock_tbot)
        await handler.start_command(mock_admin_event)
        mock_admin_event.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_command_non_admin(self, mock_tbot, mock_non_admin_event):
        """Test /start command from non-admin"""
        handler = CommandHandler(mock_tbot)
        await handler.start_command(mock_non_admin_event)
        mock_non_admin_event.respond.assert_called_once()


class TestKeywordHandler:
    """Test suite for KeywordHandler"""

    @pytest.mark.asyncio
    async def test_add_keyword_callback(self, mock_tbot, mock_callback_event):
        """Test adding keyword via callback"""
        handler = KeywordHandler(mock_tbot)
        await handler.add_keyword_handler(mock_callback_event)
        mock_callback_event.respond.assert_called_once()
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'add_keyword_handler'

    @pytest.mark.asyncio
    async def test_add_keyword_message(self, mock_tbot, mock_event):
        """Test adding keyword via message"""
        mock_event.message.text = "test_keyword"
        mock_tbot._conversations[mock_event.chat_id] = 'add_keyword_handler'
        mock_tbot.config = {"KEYWORDS": []}
        
        handler = KeywordHandler(mock_tbot)
        await handler.add_keyword_handler(mock_event)
        
        assert "test_keyword" in mock_tbot.config['KEYWORDS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_remove_keyword(self, mock_tbot, mock_event):
        """Test removing keyword"""
        mock_event.message.text = "test_keyword"
        mock_tbot._conversations[mock_event.chat_id] = 'remove_keyword_handler'
        mock_tbot.config = {"KEYWORDS": ["test_keyword"]}
        
        handler = KeywordHandler(mock_tbot)
        await handler.remove_keyword_handler(mock_event)
        
        assert "test_keyword" not in mock_tbot.config['KEYWORDS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_ignore_user_handler(self, mock_tbot, mock_event):
        """Test ignoring user"""
        mock_event.message.text = "123456789"
        mock_tbot._conversations[mock_event.chat_id] = 'ignore_user_handler'
        mock_tbot.config = {"IGNORE_USERS": []}
        
        handler = KeywordHandler(mock_tbot)
        await handler.ignore_user_handler(mock_event)
        
        assert 123456789 in mock_tbot.config['IGNORE_USERS']
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_delete_ignore_user_handler(self, mock_tbot, mock_event):
        """Test removing user from ignore list"""
        mock_event.message.text = "123456789"
        mock_tbot._conversations[mock_event.chat_id] = 'delete_ignore_user_handler'
        mock_tbot.config = {"IGNORE_USERS": [123456789]}
        
        handler = KeywordHandler(mock_tbot)
        await handler.delete_ignore_user_handler(mock_event)
        
        assert 123456789 not in mock_tbot.config['IGNORE_USERS']
        mock_event.respond.assert_called()


class TestMessageHandler:
    """Test suite for MessageHandler"""

    @pytest.mark.asyncio
    async def test_message_handler_no_conversation(self, mock_tbot, mock_event):
        """Test message handler when no conversation is active"""
        handler = MessageHandler(mock_tbot)
        result = await handler.message_handler(mock_event)
        assert result is False

    @pytest.mark.asyncio
    async def test_message_handler_phone_number(self, mock_tbot, mock_event):
        """Test message handler for phone number input"""
        mock_tbot._conversations[mock_event.chat_id] = 'phone_number_handler'
        mock_event.message.text = "+1234567890"
        
        handler = MessageHandler(mock_tbot)
        handler.account_handler.phone_number_handler = AsyncMock()
        
        result = await handler.message_handler(mock_event)
        assert result is True
        handler.account_handler.phone_number_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_handler_code(self, mock_tbot, mock_event):
        """Test message handler for code input"""
        mock_tbot._conversations[mock_event.chat_id] = 'code_handler'
        mock_event.message.text = "12345"
        
        handler = MessageHandler(mock_tbot)
        handler.account_handler.code_handler = AsyncMock()
        
        result = await handler.message_handler(mock_event)
        assert result is True
        handler.account_handler.code_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_handler_non_admin(self, mock_tbot, mock_non_admin_event, monkeypatch):
        """Test message handler rejects non-admin"""
        # Patch ADMIN_ID for this test
        monkeypatch.setattr('src.Handlers.ADMIN_ID', 123456789)
        
        handler = MessageHandler(mock_tbot)
        result = await handler.message_handler(mock_non_admin_event)
        # Should return False for non-admin
        assert result is False
        mock_non_admin_event.respond.assert_called_once()


class TestStatsHandler:
    """Test suite for StatsHandler"""

    @pytest.mark.asyncio
    async def test_show_stats(self, mock_tbot, mock_event):
        """Test showing statistics"""
        mock_tbot.config = {
            "clients": {"test1": [], "test2": []},
            "KEYWORDS": ["test"],
            "IGNORE_USERS": [123]
        }
        mock_tbot.active_clients = {"test1": MagicMock()}
        
        handler = StatsHandler(mock_tbot)
        await handler.show_stats(mock_event)
        
        mock_event.respond.assert_called_once()
        call_args = mock_event.respond.call_args[0][0]
        assert "Total Accounts" in call_args
        assert "Active Accounts" in call_args

    @pytest.mark.asyncio
    async def test_show_groups(self, mock_tbot, mock_event):
        """Test showing groups"""
        mock_tbot.config = {
            "clients": {
                "test1": [123, 456],
                "test2": [789]
            }
        }
        
        handler = StatsHandler(mock_tbot)
        await handler.show_groups(mock_event)
        
        mock_event.respond.assert_called_once()
        call_args = mock_event.respond.call_args[0][0]
        assert "Groups" in call_args

    @pytest.mark.asyncio
    async def test_show_groups_empty(self, mock_tbot, mock_event):
        """Test showing groups when none exist"""
        mock_tbot.config = {"clients": {}}
        
        handler = StatsHandler(mock_tbot)
        await handler.show_groups(mock_event)
        
        mock_event.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_keywords(self, mock_tbot, mock_event):
        """Test showing keywords"""
        mock_tbot.config = {"KEYWORDS": ["test", "keyword"]}
        
        handler = StatsHandler(mock_tbot)
        await handler.show_keywords(mock_event)
        
        mock_event.respond.assert_called_once()
        call_args = mock_event.respond.call_args[0][0]
        assert "test" in call_args or "keyword" in call_args

    @pytest.mark.asyncio
    async def test_show_keywords_empty(self, mock_tbot, mock_event):
        """Test showing keywords when none exist"""
        mock_tbot.config = {"KEYWORDS": []}
        
        handler = StatsHandler(mock_tbot)
        await handler.show_keywords(mock_event)
        
        mock_event.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_ignores(self, mock_tbot, mock_event):
        """Test showing ignored users"""
        mock_tbot.config = {"IGNORE_USERS": [123456789, 987654321]}
        
        handler = StatsHandler(mock_tbot)
        await handler.show_ignores(mock_event)
        
        mock_event.respond.assert_called_once()
        call_args = mock_event.respond.call_args[0][0]
        assert "123456789" in call_args or "987654321" in call_args


class TestCallbackHandler:
    """Test suite for CallbackHandler"""

    @pytest.mark.asyncio
    async def test_callback_handler_add_account(self, mock_tbot, mock_callback_event):
        """Test callback for add_account"""
        mock_callback_event.data = b'add_account'
        
        handler = CallbackHandler(mock_tbot)
        handler.account_handler.add_account = AsyncMock()
        # Update callback_actions to use the mocked method
        handler.callback_actions['add_account'] = handler.account_handler.add_account
        
        await handler.callback_handler(mock_callback_event)
        handler.account_handler.add_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_handler_cancel(self, mock_tbot, mock_callback_event):
        """Test callback for cancel"""
        mock_callback_event.data = b'cancel'
        mock_tbot._conversations[mock_callback_event.chat_id] = 'test_handler'
        
        handler = CallbackHandler(mock_tbot)
        await handler.callback_handler(mock_callback_event)
        
        assert mock_callback_event.chat_id not in mock_tbot._conversations
        mock_callback_event.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_handler_list_accounts(self, mock_tbot, mock_callback_event):
        """Test callback for list_accounts"""
        mock_callback_event.data = b'list_accounts'
        
        handler = CallbackHandler(mock_tbot)
        handler.account_handler.show_accounts = AsyncMock()
        handler.callback_actions['list_accounts'] = handler.account_handler.show_accounts
        
        await handler.callback_handler(mock_callback_event)
        handler.account_handler.show_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_handler_show_stats(self, mock_tbot, mock_callback_event):
        """Test callback for show_stats"""
        mock_callback_event.data = b'show_stats'
        
        handler = CallbackHandler(mock_tbot)
        handler.stats_handler.show_stats = AsyncMock()
        handler.callback_actions['show_stats'] = handler.stats_handler.show_stats
        
        await handler.callback_handler(mock_callback_event)
        handler.stats_handler.show_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_handler_bulk_reaction(self, mock_tbot, mock_callback_event):
        """Test callback for bulk_reaction"""
        mock_callback_event.data = b'bulk_reaction'
        
        handler = CallbackHandler(mock_tbot)
        handler.handle_bulk_reaction = AsyncMock()
        handler.callback_actions['bulk_reaction'] = handler.handle_bulk_reaction
        
        await handler.callback_handler(mock_callback_event)
        handler.handle_bulk_reaction.assert_called_once_with(mock_callback_event)

    @pytest.mark.asyncio
    async def test_callback_handler_unknown(self, mock_tbot, mock_callback_event):
        """Test callback for unknown command"""
        mock_callback_event.data = b'unknown_command'
        
        handler = CallbackHandler(mock_tbot)
        await handler.callback_handler(mock_callback_event)
        
        mock_callback_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_callback_handler_non_admin(self, mock_tbot, mock_callback_event, monkeypatch):
        """Test callback handler rejects non-admin"""
        # Patch ADMIN_ID for this test
        monkeypatch.setattr('src.Handlers.ADMIN_ID', 123456789)
        
        mock_callback_event.sender_id = 999999999  # Non-admin
        
        handler = CallbackHandler(mock_tbot)
        await handler.callback_handler(mock_callback_event)
        
        mock_callback_event.respond.assert_called_once()

