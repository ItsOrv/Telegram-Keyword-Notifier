#!/usr/bin/env python3
"""
Test script to verify all handlers are properly configured
"""
import sys
import os
import inspect

# Set mock environment variables before importing
os.environ['API_ID'] = '12345'
os.environ['API_HASH'] = 'test_hash'
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['ADMIN_ID'] = '123456789'
os.environ['CHANNEL_ID'] = '@test_channel'

from src.Keyboards import Keyboard
from src.Handlers import CallbackHandler, MessageHandler
from src.actions import Actions

def get_all_buttons():
    """Extract all button data from keyboards"""
    buttons = {}
    
    # Start keyboard
    start_kb = Keyboard.start_keyboard()
    for row in start_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                buttons[btn.data.decode() if isinstance(btn.data, bytes) else btn.data] = 'start'
    
    # Monitor keyboard
    monitor_kb = Keyboard.monitor_keyboard()
    for row in monitor_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                buttons[btn.data.decode() if isinstance(btn.data, bytes) else btn.data] = 'monitor'
    
    # Bulk keyboard
    bulk_kb = Keyboard.bulk_keyboard()
    for row in bulk_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                buttons[btn.data.decode() if isinstance(btn.data, bytes) else btn.data] = 'bulk'
    
    # Account management keyboard
    account_kb = Keyboard.account_management_keyboard()
    for row in account_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                buttons[btn.data.decode() if isinstance(btn.data, bytes) else btn.data] = 'account'
    
    # Individual keyboard
    individual_kb = Keyboard.individual_keyboard()
    for row in individual_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                buttons[btn.data.decode() if isinstance(btn.data, bytes) else btn.data] = 'individual'
    
    # Report keyboard
    report_kb = Keyboard.report_keyboard()
    for row in report_kb:
        for btn in row:
            if hasattr(btn, 'data'):
                buttons[btn.data.decode() if isinstance(btn.data, bytes) else btn.data] = 'report'
    
    return buttons

def check_callback_handlers():
    """Check if all callback handlers exist"""
    print("\n" + "="*60)
    print("بررسی Callback Handlers")
    print("="*60)
    
    # Create a mock tbot for testing
    class MockTbot:
        def __init__(self):
            self.active_clients = {}
            self.active_clients_lock = None
            self._conversations = {}
            self._conversations_lock = None
            self.handlers = {}
            self.config = {'KEYWORDS': [], 'IGNORE_USERS': [], 'clients': {}}
            self.config_manager = None
            self.client_manager = None
            self.monitor = None
            self.tbot = None
    
    mock_tbot = MockTbot()
    callback_handler = CallbackHandler(mock_tbot)
    
    buttons = get_all_buttons()
    missing_handlers = []
    
    for button_data, keyboard_name in buttons.items():
        # Skip dynamic buttons (with numbers or session names)
        if button_data in ['cancel', 'exit']:
            continue
        
        # Check if handler exists
        handler_exists = False
        
        # Check in callback_actions
        if hasattr(callback_handler, 'callback_actions') and button_data in callback_handler.callback_actions:
            handler_exists = True
        
        # Check for special handlers (toggle_, delete_, ignore_, reaction buttons)
        if button_data.startswith('toggle_') or button_data.startswith('delete_') or button_data.startswith('ignore_'):
            handler_exists = True
        
        # Check for reaction emoji buttons
        if button_data in ['reaction_thumbsup', 'reaction_heart', 'reaction_laugh', 'reaction_wow', 'reaction_sad', 'reaction_angry']:
            handler_exists = True
        
        # Check for bulk/individual action buttons with numbers
        if '_' in button_data:
            parts = button_data.split('_')
            if len(parts) == 2:
                action_name, value = parts
                if value.isdigit() and action_name in ['reaction', 'poll', 'join', 'block', 'send_pv', 'comment']:
                    handler_exists = True
                elif action_name in ['reaction', 'send_pv', 'join', 'left', 'comment']:
                    handler_exists = True
        
        if not handler_exists:
            missing_handlers.append((button_data, keyboard_name))
    
    if missing_handlers:
        print("❌ Handler های گمشده:")
        for btn, kb in missing_handlers:
            print(f"  - {btn} (از keyboard: {kb})")
        return False
    else:
        print("✅ تمام دکمه‌ها handler دارند")
        return True

def check_message_handlers():
    """Check if all conversation states have handlers"""
    print("\n" + "="*60)
    print("بررسی Message Handlers")
    print("="*60)
    
    # All conversation states that should be handled
    required_states = [
        'phone_number_handler',
        'code_handler',
        'password_handler',
        'ignore_user_handler',
        'delete_ignore_user_handler',
        'add_keyword_handler',
        'remove_keyword_handler',
        'reaction_link_handler',
        'poll_link_handler',
        'poll_option_handler',
        'join_link_handler',
        'left_link_handler',
        'block_user_handler',
        'send_pv_user_handler',
        'send_pv_message_handler',
        'comment_link_handler',
        'comment_text_handler',
        'bulk_join_link_handler',
        'bulk_block_user_handler',
        'bulk_send_pv_user_handler',
        'bulk_send_pv_message_handler',
    ]
    
    class MockTbot:
        def __init__(self):
            self.active_clients = {}
            self.active_clients_lock = None
            self._conversations = {}
            self._conversations_lock = None
            self.handlers = {}
            self.config = {'KEYWORDS': [], 'IGNORE_USERS': [], 'clients': {}}
            self.config_manager = None
            self.client_manager = None
            self.monitor = None
            self.tbot = None
    
    mock_tbot = MockTbot()
    message_handler = MessageHandler(mock_tbot)
    
    # Get handler method source code
    import inspect
    source = inspect.getsource(message_handler.message_handler)
    
    missing_states = []
    for state in required_states:
        if f"handler_name == '{state}'" not in source:
            missing_states.append(state)
    
    if missing_states:
        print("❌ Conversation state های بدون handler:")
        for state in missing_states:
            print(f"  - {state}")
        return False
    else:
        print("✅ تمام conversation state ها handler دارند")
        return True

def check_action_methods():
    """Check if all action methods exist"""
    print("\n" + "="*60)
    print("بررسی Action Methods")
    print("="*60)
    
    class MockTbot:
        def __init__(self):
            self.active_clients = {}
            self.active_clients_lock = None
            self._conversations = {}
            self._conversations_lock = None
            self.handlers = {}
            self.config = {'KEYWORDS': [], 'IGNORE_USERS': [], 'clients': {}}
            self.config_manager = None
            self.client_manager = None
            self.monitor = None
            self.tbot = None
    
    mock_tbot = MockTbot()
    actions = Actions(mock_tbot)
    
    required_methods = [
        'bulk_reaction',
        'bulk_poll',
        'bulk_join',
        'bulk_block',
        'bulk_send_pv',
        'bulk_comment',
        'reaction',
        'poll',
        'join',
        'left',
        'block',
        'send_pv',
        'comment',
        'reaction_link_handler',
        'reaction_select_handler',
        'poll_link_handler',
        'poll_option_handler',
        'join_link_handler',
        'left_link_handler',
        'block_user_handler',
        'send_pv_user_handler',
        'send_pv_message_handler',
        'comment_link_handler',
        'comment_text_handler',
        'bulk_join_link_handler',
        'bulk_block_user_handler',
        'bulk_send_pv_user_handler',
        'bulk_send_pv_message_handler',
        'apply_reaction',
        'parse_telegram_link',
        'handle_group_action',
        'handle_individual_action',
        'prompt_group_action',
        'prompt_individual_action',
    ]
    
    missing_methods = []
    for method_name in required_methods:
        if not hasattr(actions, method_name):
            missing_methods.append(method_name)
        elif not callable(getattr(actions, method_name)):
            missing_methods.append(method_name)
    
    if missing_methods:
        print("❌ متدهای گمشده:")
        for method in missing_methods:
            print(f"  - {method}")
        return False
    else:
        print("✅ تمام متدهای مورد نیاز وجود دارند")
        return True

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("بررسی کامل Handler ها")
    print("="*60)
    
    results = []
    
    # Check callback handlers
    results.append(("Callback Handlers", check_callback_handlers()))
    
    # Check message handlers
    results.append(("Message Handlers", check_message_handlers()))
    
    # Check action methods
    results.append(("Action Methods", check_action_methods()))
    
    # Summary
    print("\n" + "="*60)
    print("خلاصه نتایج")
    print("="*60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n✅ تمام بررسی‌ها موفق بودند!")
        return 0
    else:
        print("\n❌ برخی بررسی‌ها ناموفق بودند!")
        return 1

if __name__ == '__main__':
    sys.exit(main())

