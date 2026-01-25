"""
Unit tests for Keyboard class
"""
import pytest
from telethon import Button
from src.Keyboards import Keyboard


class TestKeyboard:
    """Test suite for Keyboard class"""

    def test_start_keyboard(self):
        """Test start keyboard structure"""
        keyboard = Keyboard.start_keyboard()
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for main menu buttons
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Account Management" in button_texts
        assert "Individual" in button_texts or "Bulk" in button_texts
        assert "Monitor Mode" in button_texts
        assert "Report status" in button_texts or "Report" in button_texts

    def test_monitor_keyboard(self):
        """Test monitor keyboard structure"""
        keyboard = Keyboard.monitor_keyboard()
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for monitor buttons
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Add Keyword" in button_texts or b'add_keyword' in [btn.data for row in keyboard for btn in row]
        assert "Remove Keyword" in button_texts or b'remove_keyword' in [btn.data for row in keyboard for btn in row]
        assert "Ignore User" in button_texts or b'ignore_user' in [btn.data for row in keyboard for btn in row]

    def test_bulk_keyboard(self):
        """Test bulk operations keyboard"""
        keyboard = Keyboard.bulk_keyboard()
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for bulk operation buttons
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Reaction" in button_texts
        assert "Poll" in button_texts
        assert "Join" in button_texts
        assert "Block" in button_texts
        assert "Send pv" in button_texts
        assert "Comment" in button_texts

    def test_account_management_keyboard(self):
        """Test account management keyboard"""
        keyboard = Keyboard.account_management_keyboard()
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for account management buttons
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Add Account" in button_texts
        assert "List Accounts" in button_texts

    def test_channel_message_keyboard(self):
        """Test channel message keyboard"""
        message_link = "https://t.me/test/123"
        sender_id = 123456789
        keyboard = Keyboard.channel_message_keyboard(message_link, sender_id)
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for URL button and ignore button
        has_url_button = any(
            hasattr(btn, 'url') and btn.url == message_link
            for row in keyboard for btn in row
        )
        has_ignore_button = any(
            hasattr(btn, 'data') and f"ignore_{sender_id}" in str(btn.data)
            for row in keyboard for btn in row
        )
        assert has_url_button or has_ignore_button

    def test_toggle_and_delete_keyboard_active(self):
        """Test toggle and delete keyboard for active account"""
        status = "🟢 Active"
        session = "test_session"
        keyboard = Keyboard.toggle_and_delete_keyboard(status, session)
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Should have disable button
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Disable" in " ".join(button_texts) or "❌ Disable" in button_texts

    def test_toggle_and_delete_keyboard_inactive(self):
        """Test toggle and delete keyboard for inactive account"""
        status = "🔴 Inactive"
        session = "test_session"
        keyboard = Keyboard.toggle_and_delete_keyboard(status, session)
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Should have enable button
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Enable" in " ".join(button_texts) or "✅ Enable" in button_texts

    def test_individual_keyboard(self):
        """Test individual operations keyboard"""
        keyboard = Keyboard.individual_keyboard()
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for individual operation buttons
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Reaction" in button_texts
        assert "Send PV" in button_texts
        assert "Join" in button_texts
        assert "Left" in button_texts
        assert "Comment" in button_texts

    def test_report_keyboard(self):
        """Test report keyboard"""
        keyboard = Keyboard.report_keyboard()
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        # Check for report buttons
        button_texts = [btn.text for row in keyboard for btn in row]
        assert "Show Stats" in button_texts

    @pytest.mark.asyncio
    async def test_show_keyboard_start(self, mock_event):
        """Test showing start keyboard"""
        keyboard = await Keyboard.show_keyboard('start', mock_event)
        assert keyboard is not None
        assert isinstance(keyboard, list)
        mock_event.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_keyboard_monitor(self, mock_event):
        """Test showing monitor keyboard"""
        keyboard = await Keyboard.show_keyboard('monitor', mock_event)
        assert keyboard is not None
        assert isinstance(keyboard, list)
        mock_event.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_keyboard_bulk(self, mock_event):
        """Test showing bulk keyboard"""
        keyboard = await Keyboard.show_keyboard('bulk', mock_event)
        assert keyboard is not None
        assert isinstance(keyboard, list)
        mock_event.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_keyboard_account_management(self, mock_event):
        """Test showing account management keyboard"""
        keyboard = await Keyboard.show_keyboard('account_management', mock_event)
        assert keyboard is not None
        assert isinstance(keyboard, list)
        mock_event.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_keyboard_invalid(self, mock_event):
        """Test showing invalid keyboard name"""
        result = await Keyboard.show_keyboard('invalid_keyboard', mock_event)
        # Should handle gracefully
        assert result is None or mock_event.respond.called

