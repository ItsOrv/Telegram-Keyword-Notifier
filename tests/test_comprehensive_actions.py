"""
Comprehensive tests for actions.py module
Tests all bulk and individual operations with edge cases
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telethon.errors import FloodWaitError, SessionRevokedError
from telethon.tl.types import User, Channel, Message, Poll, PollAnswer

from src.actions import Actions
from src.constants import HandlerKeys, ConversationStates


@pytest.mark.asyncio
class TestActionsInitialization:
    """Tests for Actions class initialization"""
    
    async def test_initialization(self, mock_tbot):
        """Test Actions initialization"""
        actions = Actions(mock_tbot)
        assert actions.tbot == mock_tbot
        assert actions.operation_semaphore is not None
        assert actions._counter_lock is not None


@pytest.mark.asyncio
class TestActionsHelperMethods:
    """Tests for helper methods in Actions"""
    
    async def test_check_connection_connected(self, mock_tbot, mock_telegram_client):
        """Test checking connection when connected"""
        actions = Actions(mock_tbot)
        mock_telegram_client.is_connected = Mock(return_value=True)
        
        result = await actions._check_connection(mock_telegram_client)
        assert result is True
    
    async def test_check_connection_disconnected(self, mock_tbot, mock_telegram_client):
        """Test checking connection when disconnected"""
        actions = Actions(mock_tbot)
        mock_telegram_client.is_connected = Mock(return_value=False)
        
        result = await actions._check_connection(mock_telegram_client)
        assert result is False
    
    async def test_validate_and_get_accounts_success(self, mock_tbot, mock_telegram_client):
        """Test validating and getting accounts successfully"""
        actions = Actions(mock_tbot)
        mock_tbot.active_clients = {
            "session1": mock_telegram_client,
            "session2": mock_telegram_client,
            "session3": mock_telegram_client
        }
        mock_telegram_client.is_connected = Mock(return_value=True)
        
        accounts, success = await actions._validate_and_get_accounts(2)
        assert success is True
        assert len(accounts) == 2
    
    async def test_validate_and_get_accounts_no_accounts(self, mock_tbot):
        """Test validating when no accounts available"""
        actions = Actions(mock_tbot)
        mock_tbot.active_clients = {}
        
        accounts, success = await actions._validate_and_get_accounts(2)
        assert success is False
        assert len(accounts) == 0
    
    async def test_clean_telegram_link(self, mock_tbot):
        """Test cleaning Telegram links"""
        actions = Actions(mock_tbot)
        
        test_cases = [
            ("https://t.me/test/123", "t.me/test/123"),
            ("http://t.me/test/123?param=value", "t.me/test/123"),
            ("https://t.me/test/123#fragment", "t.me/test/123"),
        ]
        
        for input_link, expected in test_cases:
            result = actions._clean_telegram_link(input_link)
            assert result == expected
    
    async def test_parse_private_channel_link(self, mock_tbot):
        """Test parsing private channel links"""
        actions = Actions(mock_tbot)
        
        link = "t.me/c/123456/789"
        result = actions._parse_private_channel_link(link)
        
        assert result is not None
        chat_id, message_id = result
        assert chat_id == -100123456
        assert message_id == 789
    
    async def test_parse_public_channel_link(self, mock_tbot, mock_telegram_client):
        """Test parsing public channel links"""
        actions = Actions(mock_tbot)
        
        mock_entity = Mock()
        mock_entity.id = 123456789
        mock_telegram_client.get_entity = AsyncMock(return_value=mock_entity)
        
        link = "t.me/testchannel/123"
        result = await actions._parse_public_channel_link(link, mock_telegram_client)
        
        assert result is not None
        entity, message_id = result
        assert message_id == 123
    
    async def test_parse_telegram_link_private(self, mock_tbot, mock_telegram_client):
        """Test parsing Telegram link (private)"""
        actions = Actions(mock_tbot)
        
        link = "https://t.me/c/123456/789"
        chat_id, message_id = await actions.parse_telegram_link(link, mock_telegram_client)
        
        assert chat_id == -100123456
        assert message_id == 789
    
    async def test_parse_telegram_link_public(self, mock_tbot, mock_telegram_client):
        """Test parsing Telegram link (public)"""
        actions = Actions(mock_tbot)
        
        mock_entity = Mock()
        mock_telegram_client.get_entity = AsyncMock(return_value=mock_entity)
        
        link = "https://t.me/testchannel/123"
        entity, message_id = await actions.parse_telegram_link(link, mock_telegram_client)
        
        assert message_id == 123


@pytest.mark.asyncio
class TestReactionOperations:
    """Tests for reaction operations"""
    
    async def test_bulk_reaction(self, mock_tbot, mock_event):
        """Test bulk reaction operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_reaction(mock_event, 3)
        
        assert mock_tbot.handlers[HandlerKeys.REACTION_NUM_ACCOUNTS] == 3
        assert mock_tbot.handlers[HandlerKeys.REACTION_IS_BULK] is True
        mock_event.respond.assert_called()
    
    async def test_reaction_individual(self, mock_tbot, mock_event, mock_telegram_client):
        """Test individual reaction operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        with patch('src.actions.prompt_for_input', new_callable=AsyncMock):
            await actions.reaction(mock_telegram_client, mock_event)
            
            assert mock_tbot.handlers[HandlerKeys.REACTION_ACCOUNT] == mock_telegram_client
            assert mock_tbot.handlers[HandlerKeys.REACTION_IS_BULK] is False
    
    async def test_reaction_link_handler_valid(self, mock_tbot, mock_event):
        """Test reaction link handler with valid link"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.reaction_link_handler(mock_event)
        
        assert mock_tbot.handlers[HandlerKeys.REACTION_LINK] == "https://t.me/test/123"
        mock_event.respond.assert_called()
    
    async def test_reaction_link_handler_invalid(self, mock_tbot, mock_event):
        """Test reaction link handler with invalid link"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "invalid link"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.reaction_link_handler(mock_event)
        
        mock_event.respond.assert_called()
        # Should show error message
    
    async def test_apply_reaction_success(self, mock_tbot, mock_telegram_client):
        """Test applying reaction successfully"""
        actions = Actions(mock_tbot)
        
        mock_entity = Mock()
        mock_telegram_client.get_entity = AsyncMock(return_value=mock_entity)
        mock_telegram_client.__call__ = AsyncMock()
        
        link = "https://t.me/test/123"
        reaction = "👍"
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock, return_value=(mock_entity, 123)):
            with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
                with patch('src.actions.ReactionEmoji', create=True):
                    await actions.apply_reaction(mock_telegram_client, link, reaction)
                    
                    mock_telegram_client.__call__.assert_called_once()


@pytest.mark.asyncio
class TestPollOperations:
    """Tests for poll operations"""
    
    async def test_bulk_poll(self, mock_tbot, mock_event):
        """Test bulk poll operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_poll(mock_event, 3)
        
        assert mock_tbot.handlers[HandlerKeys.POLL_NUM_ACCOUNTS] == 3
        assert mock_tbot.handlers[HandlerKeys.POLL_IS_BULK] is True
        mock_event.respond.assert_called()
    
    async def test_poll_link_handler(self, mock_tbot, mock_event):
        """Test poll link handler"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.poll_link_handler(mock_event)
        
        assert mock_tbot.handlers[HandlerKeys.POLL_LINK] == "https://t.me/test/123"
        mock_event.respond.assert_called()
    
    async def test_poll_option_handler_valid(self, mock_tbot, mock_event, mock_telegram_client):
        """Test poll option handler with valid option"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "1"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {
            HandlerKeys.POLL_LINK: "https://t.me/test/123",
            HandlerKeys.POLL_IS_BULK: False,
            HandlerKeys.POLL_ACCOUNT: mock_telegram_client
        }
        
        mock_poll = Mock(spec=Poll)
        mock_poll.poll = Mock()
        mock_poll.poll.answers = [Mock(), Mock(), Mock()]
        
        mock_message = Mock(spec=Message)
        mock_message.poll = mock_poll
        
        mock_entity = Mock()
        mock_telegram_client.get_messages = AsyncMock(return_value=mock_message)
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock, return_value=(mock_entity, 123)):
            with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
                with patch.object(actions, '_execute_individual_poll_vote', new_callable=AsyncMock):
                    await actions.poll_option_handler(mock_event)
                    
                    actions._execute_individual_poll_vote.assert_called_once()


@pytest.mark.asyncio
class TestJoinLeaveOperations:
    """Tests for join/leave operations"""
    
    async def test_join_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test join operation successfully"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        
        with patch('src.actions.prompt_for_input', new_callable=AsyncMock):
            await actions.join(mock_telegram_client, mock_event)
            
            assert mock_tbot.handlers[HandlerKeys.JOIN_ACCOUNT] == mock_telegram_client
    
    async def test_join_link_handler_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test join link handler successfully"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "https://t.me/testchannel"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {HandlerKeys.JOIN_ACCOUNT: mock_telegram_client}
        
        mock_entity = Mock()
        mock_telegram_client.join_chat = AsyncMock()
        
        with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
            await actions.join_link_handler(mock_event)
            
            mock_telegram_client.join_chat.assert_called_once()
            mock_event.respond.assert_called()
    
    async def test_left_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test leave operation successfully"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        
        with patch('src.actions.prompt_for_input', new_callable=AsyncMock):
            await actions.left(mock_telegram_client, mock_event)
            
            assert mock_tbot.handlers[HandlerKeys.LEFT_ACCOUNT] == mock_telegram_client
    
    async def test_left_link_handler_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test leave link handler successfully"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "https://t.me/testchannel"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {HandlerKeys.LEFT_ACCOUNT: mock_telegram_client}
        
        mock_entity = Mock()
        mock_telegram_client.get_entity = AsyncMock(return_value=mock_entity)
        mock_telegram_client.leave_chat = AsyncMock()
        
        await actions.left_link_handler(mock_event)
        
        mock_telegram_client.leave_chat.assert_called_once()
        mock_event.respond.assert_called()


@pytest.mark.asyncio
class TestBlockOperations:
    """Tests for block operations"""
    
    async def test_block_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test block operation successfully"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        
        with patch('src.actions.prompt_for_input', new_callable=AsyncMock):
            await actions.block(mock_telegram_client, mock_event)
            
            assert mock_tbot.handlers[HandlerKeys.BLOCK_ACCOUNT] == mock_telegram_client
    
    async def test_block_user_handler_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test block user handler successfully"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "123456789"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {HandlerKeys.BLOCK_ACCOUNT: mock_telegram_client}
        
        mock_entity = Mock()
        from telethon.tl.functions.contacts import BlockRequest
        
        with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
            mock_telegram_client.__call__ = AsyncMock()
            await actions.block_user_handler(mock_event)
            
            mock_telegram_client.__call__.assert_called_once()
            mock_event.respond.assert_called()


@pytest.mark.asyncio
class TestSendPVOperations:
    """Tests for send private message operations"""
    
    async def test_send_pv_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test send PV operation successfully"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        
        with patch('src.actions.prompt_for_input', new_callable=AsyncMock):
            await actions.send_pv(mock_telegram_client, mock_event)
            
            assert mock_tbot.handlers[HandlerKeys.SEND_PV_ACCOUNT] == mock_telegram_client
    
    async def test_send_pv_user_handler(self, mock_tbot, mock_event):
        """Test send PV user handler"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "123456789"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.send_pv_user_handler(mock_event)
        
        assert mock_tbot.handlers[HandlerKeys.SEND_PV_USER] == "123456789"
        mock_event.respond.assert_called()
    
    async def test_send_pv_message_handler_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test send PV message handler successfully"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "Test message"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {
            HandlerKeys.SEND_PV_ACCOUNT: mock_telegram_client,
            HandlerKeys.SEND_PV_USER: "123456789"
        }
        
        mock_entity = Mock()
        mock_telegram_client.send_message = AsyncMock()
        
        with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
            await actions.send_pv_message_handler(mock_event)
            
            mock_telegram_client.send_message.assert_called_once()
            mock_event.respond.assert_called()


@pytest.mark.asyncio
class TestCommentOperations:
    """Tests for comment operations"""
    
    async def test_comment_success(self, mock_tbot, mock_event, mock_telegram_client):
        """Test comment operation successfully"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        
        with patch('src.actions.prompt_for_input', new_callable=AsyncMock):
            await actions.comment(mock_telegram_client, mock_event)
            
            assert mock_tbot.handlers[HandlerKeys.COMMENT_ACCOUNT] == mock_telegram_client
    
    async def test_comment_link_handler(self, mock_tbot, mock_event):
        """Test comment link handler"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.comment_link_handler(mock_event)
        
        assert mock_tbot.handlers[HandlerKeys.COMMENT_LINK] == "https://t.me/test/123"
        mock_event.respond.assert_called()
    
    async def test_comment_text_handler_individual(self, mock_tbot, mock_event, mock_telegram_client):
        """Test comment text handler for individual operation"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "Test comment"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {
            HandlerKeys.COMMENT_ACCOUNT: mock_telegram_client,
            HandlerKeys.COMMENT_LINK: "https://t.me/test/123",
            HandlerKeys.COMMENT_IS_BULK: False
        }
        
        mock_entity = Mock()
        mock_telegram_client.send_message = AsyncMock()
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock, return_value=(mock_entity, 123)):
            with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
                await actions.comment_text_handler(mock_event)
                
                mock_telegram_client.send_message.assert_called_once()
                mock_event.respond.assert_called()


@pytest.mark.asyncio
class TestBulkOperations:
    """Tests for bulk operations"""
    
    async def test_bulk_join(self, mock_tbot, mock_event):
        """Test bulk join operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_join(mock_event, 3)
        
        assert mock_tbot.handlers[HandlerKeys.JOIN_NUM_ACCOUNTS] == 3
        mock_event.respond.assert_called()
    
    async def test_bulk_leave(self, mock_tbot, mock_event):
        """Test bulk leave operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_leave(mock_event, 3)
        
        assert mock_tbot.handlers[HandlerKeys.LEAVE_NUM_ACCOUNTS] == 3
        mock_event.respond.assert_called()
    
    async def test_bulk_block(self, mock_tbot, mock_event):
        """Test bulk block operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_block(mock_event, 3)
        
        assert mock_tbot.handlers[HandlerKeys.BLOCK_NUM_ACCOUNTS] == 3
        mock_event.respond.assert_called()
    
    async def test_bulk_comment(self, mock_tbot, mock_event):
        """Test bulk comment operation"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_comment(mock_event, 3)
        
        assert mock_tbot.handlers[HandlerKeys.COMMENT_NUM_ACCOUNTS] == 3
        assert mock_tbot.handlers[HandlerKeys.COMMENT_IS_BULK] is True
        mock_event.respond.assert_called()
    
    async def test_bulk_send_pv_account_count_handler(self, mock_tbot, mock_event):
        """Test bulk send PV account count handler"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "2"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.active_clients = {f"session{i}": Mock() for i in range(5)}
        mock_tbot.active_clients_lock = asyncio.Lock()
        
        await actions.bulk_send_pv_account_count_handler(mock_event)
        
        assert mock_tbot.handlers[HandlerKeys.SEND_PV_NUM_ACCOUNTS] == 2
        mock_event.respond.assert_called()
    
    async def test_bulk_send_pv_user_handler(self, mock_tbot, mock_event):
        """Test bulk send PV user handler"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "123456789"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        await actions.bulk_send_pv_user_handler(mock_event)
        
        assert mock_tbot.handlers[HandlerKeys.SEND_PV_USER] == "123456789"
        mock_event.respond.assert_called()
    
    async def test_bulk_send_pv_message_handler(self, mock_tbot, mock_event, mock_telegram_client):
        """Test bulk send PV message handler"""
        actions = Actions(mock_tbot)
        mock_event.message.text = "Test message"
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_tbot.handlers = {
            HandlerKeys.SEND_PV_USER: "123456789",
            HandlerKeys.SEND_PV_NUM_ACCOUNTS: 2
        }
        mock_tbot.active_clients = {
            "session1": mock_telegram_client,
            "session2": mock_telegram_client
        }
        mock_tbot.active_clients_lock = asyncio.Lock()
        
        mock_entity = Mock()
        mock_telegram_client.is_connected = Mock(return_value=True)
        mock_telegram_client.send_message = AsyncMock()
        
        with patch('src.actions.resolve_entity', new_callable=AsyncMock, return_value=mock_entity):
            with patch.object(actions, '_execute_bulk_operation_with_validation', new_callable=AsyncMock):
                await actions.bulk_send_pv_message_handler(mock_event)
                
                actions._execute_bulk_operation_with_validation.assert_called_once()


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling in operations"""
    
    async def test_handle_session_revoked_error(self, mock_tbot, mock_event, mock_telegram_client):
        """Test handling session revoked error"""
        actions = Actions(mock_tbot)
        mock_event.chat_id = 123
        mock_event.respond = AsyncMock()
        
        mock_telegram_client.session = Mock()
        mock_telegram_client.session.filename = "session1.session"
        
        with patch('src.actions.remove_revoked_session_completely', new_callable=AsyncMock):
            with patch('src.actions.cleanup_handlers_and_state', new_callable=AsyncMock):
                await actions._handle_session_revoked_error(
                    mock_event, mock_telegram_client, "test_operation", ["key1"], 123
                )
                
                mock_event.respond.assert_called()
    
    async def test_execute_with_retry_success(self, mock_tbot, mock_telegram_client):
        """Test execute with retry on success"""
        actions = Actions(mock_tbot)
        
        operation = AsyncMock()
        success, error = await actions._execute_with_retry(operation, mock_telegram_client)
        
        assert success is True
        assert error is None
        operation.assert_called_once()
    
    async def test_execute_with_retry_flood_wait(self, mock_tbot, mock_telegram_client):
        """Test execute with retry on FloodWaitError"""
        actions = Actions(mock_tbot)
        
        operation = AsyncMock(side_effect=[FloodWaitError(seconds=1), AsyncMock()()])
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            success, error = await actions._execute_with_retry(operation, mock_telegram_client, max_retries=2)
            
            # Should retry and succeed
            assert operation.call_count == 2
    
    async def test_execute_with_retry_session_revoked(self, mock_tbot, mock_telegram_client):
        """Test execute with retry on SessionRevokedError"""
        actions = Actions(mock_tbot)
        
        operation = AsyncMock(side_effect=SessionRevokedError())
        success, error = await actions._execute_with_retry(operation, mock_telegram_client)
        
        assert success is False
        assert isinstance(error, SessionRevokedError)

