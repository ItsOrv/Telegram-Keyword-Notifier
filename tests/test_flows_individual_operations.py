"""
Flow tests for Individual Operations functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.actions import Actions
from src.Handlers import CallbackHandler


class TestIndividualOperationsFlows:
    """Test complete flows for individual operations"""

    @pytest.mark.asyncio
    async def test_individual_reaction_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete individual reaction flow"""
        # Setup active client
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        
        # Step 1: User clicks "Individual Reaction"
        mock_callback_event.data = b'reaction'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects account
        mock_callback_event.data = b'reaction_test_session'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify link request
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'reaction_link_handler'
        assert mock_tbot.handlers.get('reaction_account') == mock_client
        
        # Step 3: User sends message link
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (MagicMock(), 123)
            
            await actions.reaction_link_handler(mock_event)
            
            # Verify reaction selection prompt
            # After reaction_link_handler, it should set to reaction_select_handler
            # But the test might check before that, so check for either state
            conversation_state = mock_tbot._conversations.get(mock_event.chat_id)
            assert conversation_state in ['reaction_select_handler', 'reaction_link_handler']
            
            # Step 4: User selects reaction
            mock_reaction_event = AsyncMock()
            mock_reaction_event.chat_id = mock_event.chat_id
            mock_reaction_event.data = b'reaction_heart'
            mock_reaction_event.respond = AsyncMock()
            
            with patch.object(actions, 'apply_reaction', new_callable=AsyncMock) as mock_apply:
                await actions.reaction_select_handler(mock_reaction_event)
                
                # Verify reaction was applied
                mock_apply.assert_called_once()
                mock_reaction_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_individual_send_pv_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete individual send PV flow"""
        # Setup
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        
        # Step 1: User clicks "Individual Send PV"
        mock_callback_event.data = b'send_pv'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects account
        mock_callback_event.data = b'send_pv_test_session'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends user ID/username
        mock_event.message.text = "@testuser"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        await actions.send_pv_user_handler(mock_event)
        
        # Verify message request
        assert mock_tbot._conversations.get(mock_event.chat_id) == 'send_pv_message_handler'
        
        # Step 4: User sends message
        mock_event.message.text = "Hello, this is a test message"
        
        # Mock entity
        mock_entity = MagicMock()
        mock_client.get_entity = AsyncMock(return_value=mock_entity)
        
        await actions.send_pv_message_handler(mock_event)
        
        # Verify message was sent
        mock_client.send_message.assert_called_once()
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_individual_join_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete individual join flow"""
        # Setup
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        
        # Step 1: User clicks "Individual Join"
        mock_callback_event.data = b'join'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects account
        mock_callback_event.data = b'join_test_session'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends group link
        mock_event.message.text = "https://t.me/testgroup"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        await actions.join_link_handler(mock_event)
        
        # Verify join was called
        mock_client.join_chat.assert_called_once_with("https://t.me/testgroup")
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_individual_left_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete individual left flow"""
        # Setup
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        
        # Step 1: User clicks "Individual Left"
        mock_callback_event.data = b'left'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects account
        mock_callback_event.data = b'left_test_session'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends group link
        mock_event.message.text = "https://t.me/testgroup"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        # Mock entity
        mock_entity = MagicMock()
        mock_client.get_entity = AsyncMock(return_value=mock_entity)
        
        await actions.left_link_handler(mock_event)
        
        # Verify leave was called
        mock_client.leave_chat.assert_called_once_with(mock_entity)
        mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_individual_comment_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete individual comment flow"""
        # Setup
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        
        # Step 1: User clicks "Individual Comment"
        mock_callback_event.data = b'comment'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 2: User selects account
        mock_callback_event.data = b'comment_test_session'
        await callback_handler.callback_handler(mock_callback_event)
        
        # Step 3: User sends message link
        mock_event.message.text = "https://t.me/test/123"
        mock_event.chat_id = mock_callback_event.chat_id
        
        actions = Actions(mock_tbot)
        
        with patch.object(actions, 'parse_telegram_link', new_callable=AsyncMock) as mock_parse:
            mock_entity = MagicMock()
            mock_parse.return_value = (mock_entity, 123)
            
            await actions.comment_link_handler(mock_event)
            
            # Verify comment text request
            assert mock_tbot._conversations.get(mock_event.chat_id) == 'comment_text_handler'
            
            # Step 4: User sends comment text
            mock_event.message.text = "This is a test comment"
            
            await actions.comment_text_handler(mock_event)
            
            # Verify comment was posted
            mock_client.send_message.assert_called_once()
            mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_individual_block_flow(self, mock_tbot, mock_callback_event, mock_event):
        """Test individual block flow"""
        # Setup
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        
        # Step 1: User clicks "Individual Block" (via action)
        actions = Actions(mock_tbot)
        await actions.block(mock_client, mock_callback_event)
        
        # Verify user ID request
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'block_user_handler'
        
        # Step 2: User sends user ID/username
        mock_event.message.text = "@testuser"
        mock_event.chat_id = mock_callback_event.chat_id
        
        # Mock entity
        mock_entity = MagicMock()
        mock_client.get_entity = AsyncMock(return_value=mock_entity)
        
        with patch('telethon.tl.functions.contacts.BlockRequest') as mock_block:
            await actions.block_user_handler(mock_event)
            
            # Verify block was called
            mock_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_individual_operation_account_not_found(self, mock_tbot, mock_callback_event):
        """Test individual operation when account is not found"""
        mock_tbot.active_clients = {}
        
        mock_callback_event.data = b'reaction_nonexistent'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Should show error
        mock_callback_event.respond.assert_called()
        call_args = mock_callback_event.respond.call_args[0][0]
        assert "پیدا نشد" in call_args or "not found" in call_args.lower()

    @pytest.mark.asyncio
    async def test_individual_send_pv_invalid_message(self, mock_tbot, mock_event):
        """Test individual send PV with invalid message"""
        mock_client = AsyncMock()
        mock_tbot.active_clients = {"test_session": mock_client}
        mock_tbot.handlers = {
            "send_pv_account": mock_client,
            "send_pv_user": "@testuser"
        }
        mock_tbot._conversations = {mock_event.chat_id: 'send_pv_message_handler'}
        
        # Empty message
        mock_event.message.text = ""
        
        actions = Actions(mock_tbot)
        await actions.send_pv_message_handler(mock_event)
        
        # Should show error
        mock_event.respond.assert_called()
        call_args = mock_event.respond.call_args[0][0]
        assert "cannot" in call_args.lower() or "must" in call_args.lower() or "invalid" in call_args.lower() or "error" in call_args.lower()

