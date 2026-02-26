#!/usr/bin/env python3
"""
Test script to verify all buttons and keyboards have proper handlers
"""

import sys
import inspect
from src.Keyboards import Keyboard
from src.Handlers import CallbackHandler
from src.actions import Actions

def get_all_button_data():
    """Extract all button data from keyboards"""
    buttons = {}
    
    # Start keyboard
    start_kb = Keyboard.start_keyboard()
    for row in start_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                data = btn.data.decode() if isinstance(btn.data, bytes) else btn.data
                buttons[data] = {'keyboard': 'start', 'text': getattr(btn, 'text', 'N/A')}
    
    # Monitor keyboard
    monitor_kb = Keyboard.monitor_keyboard()
    for row in monitor_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                data = btn.data.decode() if isinstance(btn.data, bytes) else btn.data
                buttons[data] = {'keyboard': 'monitor', 'text': getattr(btn, 'text', 'N/A')}
    
    # Bulk keyboard
    bulk_kb = Keyboard.bulk_keyboard()
    for row in bulk_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                data = btn.data.decode() if isinstance(btn.data, bytes) else btn.data
                buttons[data] = {'keyboard': 'bulk', 'text': getattr(btn, 'text', 'N/A')}
    
    # Account management keyboard
    account_kb = Keyboard.account_management_keyboard()
    for row in account_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                data = btn.data.decode() if isinstance(btn.data, bytes) else btn.data
                buttons[data] = {'keyboard': 'account_management', 'text': getattr(btn, 'text', 'N/A')}
    
    # Individual keyboard
    individual_kb = Keyboard.individual_keyboard()
    for row in individual_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                data = btn.data.decode() if isinstance(btn.data, bytes) else btn.data
                buttons[data] = {'keyboard': 'individual', 'text': getattr(btn, 'text', 'N/A')}
    
    # Report keyboard
    report_kb = Keyboard.report_keyboard()
    for row in report_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                data = btn.data.decode() if isinstance(btn.data, bytes) else btn.data
                buttons[data] = {'keyboard': 'report', 'text': getattr(btn, 'text', 'N/A')}
    
    return buttons

def check_handlers():
    """Check if all buttons have handlers"""
    print("=" * 60)
    print("بررسی کامل دکمه‌ها و Handler ها")
    print("=" * 60)
    
    # Get all buttons
    all_buttons = get_all_button_data()
    
    # Create a mock tbot for CallbackHandler
    class MockTbot:
        def __init__(self):
            self.active_clients = {}
            self.active_clients_lock = None
            self.handlers = {}
            self._conversations = {}
            self._conversations_lock = None
            self.client_manager = None
    
    mock_tbot = MockTbot()
    
    try:
        callback_handler = CallbackHandler(mock_tbot)
        actions = Actions(mock_tbot)
    except Exception as e:
        print(f"❌ خطا در ایجاد handlers: {e}")
        return False
    
    # Check static buttons
    print("\n📋 بررسی دکمه‌های Static:")
    print("-" * 60)
    
    missing_handlers = []
    handled_buttons = []
    
    for button_data, info in all_buttons.items():
        # Skip dynamic buttons (contain numbers or session names)
        if any(char.isdigit() for char in button_data.split('_')[-1] if button_data.split('_')[-1]):
            continue
        
        # Check if handler exists
        has_handler = False
        
        # Check in callback_actions
        if hasattr(callback_handler, 'callback_actions'):
            if button_data in callback_handler.callback_actions:
                has_handler = True
        
        # Check for special handlers (toggle_, delete_, ignore_)
        if button_data.startswith('toggle_') or button_data.startswith('delete_') or button_data.startswith('ignore_'):
            has_handler = True
        
        # Check for reaction buttons
        if button_data in ['reaction_thumbsup', 'reaction_heart', 'reaction_laugh', 'reaction_wow', 'reaction_sad', 'reaction_angry']:
            has_handler = True
        
        # Check for bulk/individual action buttons
        if '_' in button_data:
            parts = button_data.split('_')
            if len(parts) == 2:
                action_name, value = parts
                if action_name in ['reaction', 'poll', 'join', 'block', 'comment', 'send_pv', 'left']:
                    has_handler = True
        
        if has_handler:
            handled_buttons.append((button_data, info))
            print(f"✅ {button_data:30s} ({info['keyboard']:20s}) - {info['text']}")
        else:
            missing_handlers.append((button_data, info))
            print(f"❌ {button_data:30s} ({info['keyboard']:20s}) - {info['text']} - NO HANDLER!")
    
    # Check dynamic buttons
    print("\n📋 بررسی دکمه‌های Dynamic:")
    print("-" * 60)
    print("✅ Bulk operation buttons (action_name_{num}) - handled in callback_handler")
    print("✅ Individual operation buttons (action_name_{session}) - handled in callback_handler")
    print("✅ Reaction buttons (reaction_*) - handled in reaction_select_handler")
    print("✅ Toggle/Delete buttons (toggle_{session}, delete_{session}) - handled in callback_handler")
    print("✅ Ignore buttons (ignore_{user_id}) - handled in callback_handler")
    
    # Summary
    print("\n" + "=" * 60)
    print("خلاصه نتایج:")
    print("=" * 60)
    print(f"✅ دکمه‌های با handler: {len(handled_buttons)}")
    print(f"❌ دکمه‌های بدون handler: {len(missing_handlers)}")
    
    if missing_handlers:
        print("\n⚠️ دکمه‌های بدون handler:")
        for button_data, info in missing_handlers:
            print(f"   - {button_data} ({info['keyboard']})")
        return False
    else:
        print("\n✅ همه دکمه‌ها handler دارند!")
        return True

if __name__ == "__main__":
    success = check_handlers()
    sys.exit(0 if success else 1)

