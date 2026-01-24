"""
Flow tests for Account Management functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.Client import AccountHandler, SessionManager
from src.Handlers import CallbackHandler


class TestAccountManagementFlows:
    """Test complete flows for account management"""

    @pytest.mark.asyncio
    async def test_add_account_flow_complete(self, mock_tbot, mock_callback_event, mock_event):
        """Test complete add account flow: callback -> phone -> code -> password -> finalize"""
        # Step 1: User clicks "Add Account" button
        mock_callback_event.data = b'add_account'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify phone number request
        assert mock_tbot._conversations.get(mock_callback_event.chat_id) == 'phone_number_handler'
        
        # Step 2: User sends phone number
        mock_event.message.text = "+1234567890"
        mock_event.chat_id = mock_callback_event.chat_id
        mock_tbot.handlers = {}
        
        account_handler = AccountHandler(mock_tbot)
        account_handler.tbot.tbot.send_message = AsyncMock()
        
        # Mock client connection flow
        with patch('src.Client.TelegramClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=False)
            mock_client.connect = AsyncMock()
            mock_client.send_code_request = AsyncMock()
            mock_client_class.return_value = mock_client
            
            await account_handler.phone_number_handler(mock_event)
            
            # Verify code request
            assert mock_tbot._conversations.get(mock_event.chat_id) == 'code_handler'
            mock_client.send_code_request.assert_called_once()
            
            # Step 3: User sends verification code
            mock_event.message.text = "12345"
            mock_tbot.handlers['temp_client'] = mock_client
            mock_tbot.handlers['temp_phone'] = "+1234567890"
            
            # Mock successful sign in (no password needed)
            mock_client.sign_in = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=True)
            
            account_handler.finalize_client_setup = AsyncMock()
            await account_handler.code_handler(mock_event)
            
            # Verify finalization
            account_handler.finalize_client_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_account_flow_with_2fa(self, mock_tbot, mock_event):
        """Test add account flow with 2FA password"""
        from telethon.errors import SessionPasswordNeededError
        
        mock_event.message.text = "12345"  # Code
        mock_tbot._conversations[mock_event.chat_id] = 'code_handler'
        mock_tbot.handlers = {}
        
        from unittest.mock import MagicMock
        mock_client = AsyncMock()
        # SessionPasswordNeededError requires a request parameter
        mock_request = MagicMock()
        mock_client.sign_in = AsyncMock(side_effect=SessionPasswordNeededError(mock_request))
        mock_tbot.handlers['temp_client'] = mock_client
        mock_tbot.handlers['temp_phone'] = "+1234567890"
        
        account_handler = AccountHandler(mock_tbot)
        account_handler.tbot.tbot.send_message = AsyncMock()
        
        await account_handler.code_handler(mock_event)
        
        # Verify password request
        assert mock_tbot._conversations.get(mock_event.chat_id) == 'password_handler'
        
        # Step 4: User sends password
        mock_event.message.text = "password123"
        mock_client.sign_in = AsyncMock()  # Success this time
        
        account_handler.finalize_client_setup = AsyncMock()
        await account_handler.password_handler(mock_event)
        
        # Verify finalization
        account_handler.finalize_client_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_accounts_flow(self, mock_tbot, mock_callback_event):
        """Test listing accounts flow"""
        # Setup test data
        mock_tbot.config = {
            "clients": {
                "test_session1": [123, 456],
                "test_session2": [789]
            }
        }
        mock_tbot.active_clients = {"test_session1": MagicMock()}
        
        # User clicks "List Accounts"
        mock_callback_event.data = b'list_accounts'
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify accounts were shown
        mock_callback_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_toggle_account_flow(self, mock_tbot, mock_callback_event):
        """Test toggling account active/inactive"""
        session_name = "test_session"
        
        # Setup: account is active
        mock_client = AsyncMock()
        mock_tbot.active_clients[session_name] = mock_client
        mock_tbot.config = {"clients": {session_name: []}}
        mock_tbot.config_manager.save_config = MagicMock()
        mock_tbot.monitor = MagicMock()
        mock_tbot.monitor.cleanup_client_handlers = MagicMock()
        mock_tbot.monitor.process_messages_for_client = AsyncMock()
        
        # User clicks toggle button
        mock_callback_event.data = f"toggle_{session_name}".encode()
        
        callback_handler = CallbackHandler(mock_tbot)
        account_handler = AccountHandler(mock_tbot)
        
        with patch('src.Client.TelegramClient') as mock_client_class:
            new_client = AsyncMock()
            new_client.start = AsyncMock()
            mock_client_class.return_value = new_client
            
            await account_handler.toggle_client(session_name, mock_callback_event)
            
            # Verify account was disabled
            assert session_name not in mock_tbot.active_clients
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account_flow(self, mock_tbot, mock_callback_event):
        """Test deleting account flow"""
        session_name = "test_session"
        
        # Setup
        mock_client = AsyncMock()
        mock_tbot.active_clients[session_name] = mock_client
        mock_tbot.config = {"clients": {session_name: []}}
        mock_tbot.config_manager.save_config = MagicMock()
        mock_tbot.client_manager = MagicMock()
        mock_tbot.client_manager.delete_session = AsyncMock()
        mock_tbot.monitor = MagicMock()
        mock_tbot.monitor.cleanup_client_handlers = MagicMock()
        
        # User clicks delete button
        mock_callback_event.data = f"delete_{session_name}".encode()
        
        callback_handler = CallbackHandler(mock_tbot)
        await callback_handler.callback_handler(mock_callback_event)
        
        # Verify deletion was called
        mock_tbot.client_manager.delete_session.assert_called_once_with(session_name)

    @pytest.mark.asyncio
    async def test_update_groups_flow(self, mock_tbot, mock_callback_event):
        """Test updating groups flow"""
        import os
        import json
        
        # Setup test clients
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()
        mock_tbot.active_clients = {
            "test_session1": mock_client1,
            "test_session2": mock_client2
        }
        
        # Mock dialog iteration
        mock_dialog1 = MagicMock()
        mock_dialog1.entity.id = 123
        mock_dialog1.entity.__class__.__name__ = "Chat"
        
        mock_dialog2 = MagicMock()
        mock_dialog2.entity.id = 456
        mock_dialog2.entity.__class__.__name__ = "Channel"
        mock_dialog2.entity.broadcast = False
        
        async def mock_iter_dialogs(*args, **kwargs):
            yield mock_dialog1
            yield mock_dialog2
        
        mock_client1.iter_dialogs = mock_iter_dialogs
        mock_client2.iter_dialogs = mock_iter_dialogs
        
        # User clicks "Update Groups"
        mock_callback_event.data = b'update_groups'
        callback_handler = CallbackHandler(mock_tbot)
        
        account_handler = AccountHandler(mock_tbot)
        callback_handler.account_handler = account_handler
        
        with patch('src.Client.CLIENTS_JSON_PATH', 'test_clients.json'):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = json.dumps({"clients": {}})
                mock_file.__enter__.return_value = mock_file
                mock_open.return_value = mock_file
                
                await callback_handler.callback_handler(mock_callback_event)
                
                # Verify groups were updated
                mock_callback_event.respond.assert_called()

    @pytest.mark.asyncio
    async def test_add_account_invalid_phone(self, mock_tbot, mock_event):
        """Test adding account with invalid phone number"""
        mock_event.message.text = "invalid_phone"
        mock_tbot._conversations[mock_event.chat_id] = 'phone_number_handler'
        
        account_handler = AccountHandler(mock_tbot)
        account_handler.tbot.tbot.send_message = AsyncMock()
        
        await account_handler.phone_number_handler(mock_event)
        
        # Verify error message was sent
        account_handler.tbot.tbot.send_message.assert_called()
        call_args = account_handler.tbot.tbot.send_message.call_args
        # call_args is a tuple: (args, kwargs)
        # First arg is chat_id, second is message text
        if call_args and len(call_args[0]) > 1:
            message_text = str(call_args[0][1])
            assert "❌" in message_text or "error" in message_text.lower()
        else:
            # Check kwargs if args don't have message
            if call_args and call_args[1] and 'message' in call_args[1]:
                message_text = str(call_args[1]['message'])
                assert "❌" in message_text or "error" in message_text.lower()

    @pytest.mark.asyncio
    async def test_add_account_invalid_code(self, mock_tbot, mock_event):
        """Test adding account with invalid verification code"""
        mock_event.message.text = "wrong_code"
        mock_tbot._conversations[mock_event.chat_id] = 'code_handler'
        mock_tbot.handlers = {}
        
        mock_client = AsyncMock()
        mock_client.sign_in = AsyncMock(side_effect=Exception("Invalid code"))
        mock_tbot.handlers['temp_client'] = mock_client
        mock_tbot.handlers['temp_phone'] = "+1234567890"
        
        account_handler = AccountHandler(mock_tbot)
        account_handler.tbot.tbot.send_message = AsyncMock()
        
        await account_handler.code_handler(mock_event)
        
        # Verify error handling
        account_handler.tbot.tbot.send_message.assert_called()
        # Cleanup should be called
        assert 'temp_client' not in mock_tbot.handlers or mock_tbot.handlers.get('temp_client') is None

