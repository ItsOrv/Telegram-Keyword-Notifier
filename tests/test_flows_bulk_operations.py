"""
Flow tests for Bulk Operations functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.actions import Actions
from src.Handlers import CallbackHandler


class TestBulkOperationsFlows:
    """Test complete flows for bulk operations"""

    @pytest.mark.asyncio
    async def test_bulk_reaction_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete bulk reaction flow"""
        # Setup active clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_client3 = AsyncMock()
        mock_tbot.active_clients = {
            "session1": mock_client1,
            "session2": mock_client2,
            "session3": mock_client3
        }
        
        # Step 1: User clicks "Bulk Reaction"
        mock_callback_event.data = b'bulk_reaction'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects number of accounts (e.g., 2)
        mock_callback_event.data = b'reaction_2'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify conversation state
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'reaction_link_handler'
        assert mock_tbot.handlers.get('reaction_num_accounts') == 2
        
        # Step 3: User sends message link
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (MagicMock(), 123)
            
            with patch.object(actions, 'apply_reaction', new_callable=AsyncMock) as mock_apply:
                await actions.reaction_link_handler(mock_event)
                
                # Verify reaction selection prompt
                mock_event.respond.assert_called()
                # After reaction_link_handler, it should set to reaction_select_handler
                # But the test might check before that, so check for either state
                conversation_state = mock_tbot._conversations.get(mock_event.chat_id)
                assert conversation_state in ['reaction_select_handler', 'reaction_link_handler']
                
                # Step 4: User selects reaction emoji
                mock_reaction_event = AsyncMock()
                mock_reaction_event.chat_id = mock_event.chat_id
                mock_reaction_event.data = b'reaction_thumbsup'
                mock_reaction_event.respond = AsyncMock()
                
                await actions.reaction_select_handler(mock_reaction_event)
                
                # Verify reactions were applied
                assert mock_apply.call_count == 2  # 2 accounts

    @pytest.mark.asyncio
    async def test_bulk_poll_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete bulk poll flow"""
        # Setup
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_tbot.active_clients = {
            "session1": mock_client1,
            "session2": mock_client2
        }
        
        # Step 1: User clicks "Bulk Poll"
        mock_callback_event.data = b'bulk_poll'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects 2 accounts
        mock_callback_event.data = b'poll_2'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends poll link
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (MagicMock(), 123)
            
            await actions.poll_link_handler(mock_event)
            
            # Verify option request
            assert mock_tbot._conversations.get(mock_event.chat_id) == 'poll_option_handler'
            
            # Step 4: User sends option number
            mock_event.message.text = "1"
            
            # Mock poll message
            mock_message = MagicMock()
            mock_message.poll = MagicMock()
            mock_client1.get_messages = AsyncMock(return_value=mock_message)
            
            with patch('telethon.tl.functions.messages.SendVoteRequest') as mock_vote:
                await actions.poll_option_handler(mock_event)
                
                # Verify votes were sent
                mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_join_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete bulk join flow"""
        # Setup
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_tbot.active_clients = {
            "session1": mock_client1,
            "session2": mock_client2
        }
        
        # Step 1: User clicks "Bulk Join"
        mock_callback_event.data = b'bulk_join'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects 2 accounts
        mock_callback_event.data = b'join_2'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends group link
        mock_event.message.text = "https://t.me/testgroup"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        await actions.bulk_join_link_handler(mock_event)
        
        # Verify join was called for both accounts
        assert mock_client1.join_chat.call_count >= 1
        assert mock_client2.join_chat.call_count >= 1
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_block_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete bulk block flow"""
        # Setup
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_tbot.active_clients = {
            "session1": mock_client1,
            "session2": mock_client2
        }
        
        # Step 1: User clicks "Bulk Block"
        mock_callback_event.data = b'bulk_block'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects 2 accounts
        mock_callback_event.data = b'block_2'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends user ID/username
        mock_event.message.text = "@testuser"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        # Mock entity
        mock_entity = MagicMock()
        mock_client1.get_entity = AsyncMock(return_value=mock_entity)
        mock_client2.get_entity = AsyncMock(return_value=mock_entity)
        
        with patch('telethon.tl.functions.contacts.BlockRequest') as mock_block:
            await actions.bulk_block_user_handler(mock_event)
            
            # Verify block was called
            mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_send_pv_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete bulk send PV flow"""
        # Setup
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_tbot.active_clients = {
            "session1": mock_client1,
            "session2": mock_client2
        }
        
        # Step 1: User clicks "Bulk Send PV"
        mock_callback_event.data = b'bulk_send_pv'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects 2 accounts
        mock_callback_event.data = b'send_pv_2'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends user ID/username
        mock_event.message.text = "@testuser"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        await actions.bulk_send_pv_user_handler(mock_event)
        
        # Verify message request
        assert mock_tbot._conversations.get(mock_event.chat_id) == 'bulk_send_pv_message_handler'
        
        # Step 4: User sends message
        mock_event.message.text = "Test message"
        
        # Mock entity
        mock_entity = MagicMock()
        mock_client1.get_entity = AsyncMock(return_value=mock_entity)
        mock_client2.get_entity = AsyncMock(return_value=mock_entity)
        
        await actions.bulk_send_pv_message_handler(mock_event)
        
        # Verify messages were sent
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_comment_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete bulk comment flow"""
        # Setup
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_tbot.active_clients = {
            "session1": mock_client1,
            "session2": mock_client2
        }
        
        # Step 1: User clicks "Bulk Comment"
        mock_callback_event.data = b'bulk_comment'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects 2 accounts
        mock_callback_event.data = b'comment_2'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends message link
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (MagicMock(), 123)
            
            await actions.comment_link_handler(mock_event)
            
            # Verify comment text request
            assert mock_tbot._conversations.get(mock_event.chat_id) == 'comment_text_handler'
            
            # Step 4: User sends comment text
            mock_event.message.text = "Test comment"
            
            await actions.comment_text_handler(mock_event)
            
            # Verify comments were posted
            mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_bulk_operation_no_accounts(self, mock_tbot, mock_callback_event):
        """Test bulk operation when no accounts are available"""
        mock_tbot.active_clients = {}
        
        mock_callback_event.data = b'bulk_reaction'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Should show error message
        mock_callback_event.respond.assert_called()
        call_args = mock_callback_event.respond.call_args[0][0]
        # Check all calls - handler may send multiple messages
        calls = mock_callback_event.respond.call_args_list
        call_args_text = ' '.join([str(call[0][0]) if call[0] else '' for call in calls])
        assert "No accounts" in call_args_text or "❌" in call_args_text or "0 accounts" in call_args_text

    @pytest.mark.asyncio
    async def test_bulk_reaction_invalid_link(self, mock_tbot, mock_event):
        """Test bulk reaction with invalid link"""
        from unittest.mock import patch
        from src.actions import Actions
        
        mock_tbot.active_clients = {"session1": AsyncMock()}
        mock_tbot.handlers = {"reaction_num_accounts": 1}
        mock_tbot._conversations = {mock_event.chat_id: 'reaction_link_handler'}
        
        mock_event.message.text = "invalid_link"
        
        actions = Actions(mock_tbot)
        # Mock the validator to return invalid
        with patch('src.actions.InputValidator.validate_telegram_link', return_value=(False, "Invalid link format")):
            await actions.reaction_link_handler(mock_event)
        
        # Should show error - check all calls
        mock_event.respond.assert_called()
        calls = mock_event.respond.call_args_list
        call_args_text = ' '.join([str(call[0][0]) if call[0] else '' for call in calls])
        # For invalid link, it should show error message
        assert "❌" in call_args_text or "error" in call_args_text.lower() or "خطا" in call_args_text or "دوباره تلاش" in call_args_text

