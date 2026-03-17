"""
Comprehensive tests for Monitor.py module
Tests message monitoring and forwarding functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telethon import events
from telethon.tl.types import User, Channel, Chat, Message

from src.Monitor import Monitor


@pytest.mark.asyncio
class TestMonitorInitialization:
    """Tests for Monitor class initialization"""
    
    async def test_initialization(self, mock_tbot):
        """Test Monitor initialization"""
        monitor = Monitor(mock_tbot)
        assert monitor.tbot == mock_tbot
        assert monitor.channel_id is None
        assert monitor.channel_username is None


@pytest.mark.asyncio
class TestResolveChannelId:
    """Tests for channel ID resolution"""
    
    async def test_resolve_username(self, mock_tbot):
        """Test resolving channel username to ID"""
        monitor = Monitor(mock_tbot)
        
        mock_entity = Mock()
        mock_entity.id = 123456789
        mock_entity.username = "testchannel"
        mock_tbot.tbot.get_entity = AsyncMock(return_value=mock_entity)
        
        with patch('src.Monitor.CHANNEL_ID', 'testchannel'):
            await monitor.resolve_channel_id()
            
            assert monitor.channel_id == 123456789
            assert monitor.channel_username == "testchannel"
    
    async def test_resolve_numeric_id(self, mock_tbot):
        """Test resolving numeric channel ID"""
        monitor = Monitor(mock_tbot)
        
        with patch('src.Monitor.CHANNEL_ID', '123456789'):
            await monitor.resolve_channel_id()
            
            assert monitor.channel_id == 123456789
    
    async def test_resolve_not_configured(self, mock_tbot):
        """Test when channel ID is not configured"""
        monitor = Monitor(mock_tbot)
        
        with patch('src.Monitor.CHANNEL_ID', None):
            await monitor.resolve_channel_id()
            
            assert monitor.channel_id is None
    
    async def test_resolve_already_resolved(self, mock_tbot):
        """Test when channel ID is already resolved"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        await monitor.resolve_channel_id()
        
        # Should not call get_entity again
        assert monitor.channel_id == 123456789


@pytest.mark.asyncio
class TestProcessMessagesForClient:
    """Tests for processing messages for a client"""
    
    async def test_setup_message_processing(self, mock_tbot, mock_telegram_client):
        """Test setting up message processing for a client"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_telegram_client.on = Mock(return_value=Mock())
        mock_telegram_client._registered_handlers = []
        
        await monitor.process_messages_for_client(mock_telegram_client)
        
        assert mock_telegram_client.on.called
        assert len(mock_telegram_client._registered_handlers) == 1
    
    async def test_process_message_with_keyword(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test processing message containing keyword"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        mock_new_message_event.id = 1
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321
        mock_sender.first_name = "Test"
        mock_sender.last_name = "User"
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_chat.username = "testchannel"
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        # Create handler function
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        
        # Simulate message event
        await handler(mock_new_message_event)
        
        mock_tbot.tbot.send_message.assert_called_once()
        call_args = mock_tbot.tbot.send_message.call_args
        assert call_args[0][0] == 123456789
        assert "test" in call_args[0][1].lower()
    
    async def test_process_message_no_keyword(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test processing message without keyword"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['keyword'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This message has no keyword"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        # Should not send message
        mock_tbot.tbot.send_message.assert_not_called()
    
    async def test_process_message_ignored_user(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test processing message from ignored user"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': [987654321]
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321  # Ignored user
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        # Should not send message for ignored user
        mock_tbot.tbot.send_message.assert_not_called()
    
    async def test_process_message_from_channel(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test processing message sent to the channel itself"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = 123456789  # Same as channel_id
        mock_new_message_event.out = False
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        # Should not send message to avoid loops
        mock_tbot.tbot.send_message.assert_not_called()
    
    async def test_process_message_from_bot(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test processing message sent by bot itself"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = True  # Sent by bot
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        # Should not send message to avoid loops
        mock_tbot.tbot.send_message.assert_not_called()
    
    async def test_process_message_public_channel_link(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test generating link for public channel"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        mock_new_message_event.id = 123
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321
        mock_sender.first_name = "Test"
        mock_sender.last_name = "User"
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_chat.username = "testchannel"  # Public channel
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        mock_tbot.tbot.send_message.assert_called_once()
        call_args = mock_tbot.tbot.send_message.call_args
        # Check that buttons were created with link
        assert call_args[1]['buttons'] is not None
    
    async def test_process_message_private_channel_link(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test generating link for private channel"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        mock_new_message_event.id = 123
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321
        mock_sender.first_name = "Test"
        mock_sender.last_name = "User"
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_chat.username = None  # Private channel
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        mock_tbot.tbot.send_message.assert_called_once()
        call_args = mock_tbot.tbot.send_message.call_args
        # Check that buttons were created with private link format
        assert call_args[1]['buttons'] is not None
    
    async def test_process_message_empty_text(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test processing message with empty text"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = None
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        await handler(mock_new_message_event)
        
        # Should not send message (no keyword match with empty text)
        mock_tbot.tbot.send_message.assert_not_called()
    
    async def test_process_message_unicode_error(self, mock_tbot, mock_new_message_event, mock_telegram_client):
        """Test handling UnicodeEncodeError"""
        monitor = Monitor(mock_tbot)
        monitor.channel_id = 123456789
        
        mock_tbot.config = {
            'KEYWORDS': ['test'],
            'IGNORE_USERS': []
        }
        mock_tbot.tbot.send_message = AsyncMock()
        
        mock_new_message_event.message.text = "This is a test message"
        mock_new_message_event.chat_id = -1001234567890
        mock_new_message_event.out = False
        
        mock_sender = Mock(spec=User)
        mock_sender.id = 987654321
        mock_sender.first_name = "Test"
        mock_sender.last_name = "User"
        mock_new_message_event.get_sender = AsyncMock(return_value=mock_sender)
        
        mock_chat = Mock(spec=Channel)
        mock_chat.id = -1001234567890
        mock_chat.title = "Test Channel"
        mock_chat.username = "testchannel"
        mock_new_message_event.get_chat = AsyncMock(return_value=mock_chat)
        
        # Make send_message raise UnicodeEncodeError
        mock_tbot.tbot.send_message = AsyncMock(side_effect=UnicodeEncodeError('utf-8', 'test', 0, 1, 'error'))
        
        handler = await monitor.process_messages_for_client(mock_telegram_client)
        
        # Should handle error gracefully
        try:
            await handler(mock_new_message_event)
        except UnicodeEncodeError:
            pytest.fail("UnicodeEncodeError was not handled")


@pytest.mark.asyncio
class TestCleanupClientHandlers:
    """Tests for cleaning up client handlers"""
    
    async def test_cleanup_handlers(self, mock_tbot, mock_telegram_client):
        """Test cleaning up handlers for a client"""
        monitor = Monitor(mock_tbot)
        
        mock_handler1 = Mock()
        mock_handler2 = Mock()
        mock_telegram_client._registered_handlers = [mock_handler1, mock_handler2]
        mock_telegram_client.remove_event_handler = Mock()
        
        monitor.cleanup_client_handlers(mock_telegram_client)
        
        assert mock_telegram_client.remove_event_handler.call_count == 2
        assert len(mock_telegram_client._registered_handlers) == 0
    
    async def test_cleanup_handlers_no_handlers(self, mock_tbot, mock_telegram_client):
        """Test cleaning up when no handlers exist"""
        monitor = Monitor(mock_tbot)
        
        del mock_telegram_client._registered_handlers
        
        # Should not raise error
        monitor.cleanup_client_handlers(mock_telegram_client)
    
    async def test_cleanup_handlers_error(self, mock_tbot, mock_telegram_client):
        """Test handling errors during cleanup"""
        monitor = Monitor(mock_tbot)
        
        mock_handler = Mock()
        mock_telegram_client._registered_handlers = [mock_handler]
        mock_telegram_client.remove_event_handler = Mock(side_effect=Exception("Error"))
        
        # Should handle error gracefully
        monitor.cleanup_client_handlers(mock_telegram_client)
        
        assert len(mock_telegram_client._registered_handlers) == 0

