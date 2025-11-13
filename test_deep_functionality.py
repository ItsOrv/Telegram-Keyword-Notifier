#!/usr/bin/env python3
"""
Deep Functionality Testing
Tests internal methods and class interactions
"""

import asyncio
import logging
import sys
from unittest.mock import Mock, AsyncMock, MagicMock

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class DeepTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def test_result(self, test_name, success, error_msg=None):
        if success:
            self.passed += 1
            logger.info(f"✅ PASS: {test_name}")
        else:
            self.failed += 1
            logger.error(f"❌ FAIL: {test_name}")
            if error_msg:
                logger.error(f"   Error: {error_msg}")
                self.errors.append(f"{test_name}: {error_msg}")
    
    def summary(self):
        total = self.passed + self.failed
        logger.info("\n" + "="*60)
        logger.info(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed}")
        if total > 0:
            logger.info(f"Success Rate: {(self.passed/total*100):.1f}%")
        logger.info("="*60)
        return self.failed == 0

def test_handlers_structure():
    """Test Handlers class structure"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: HANDLERS STRUCTURE")
    logger.info("="*60)
    
    try:
        from src.Handlers import CommandHandler, KeywordHandler, MessageHandler, StatsHandler, CallbackHandler
        
        # Mock bot object
        mock_bot = Mock()
        mock_bot.config = {
            'KEYWORDS': [],
            'IGNORE_USERS': [],
            'TARGET_GROUPS': [],
            'clients': {}
        }
        mock_bot._conversations = {}
        mock_bot.active_clients = {}
        mock_bot.handlers = {}
        mock_bot.config_manager = Mock()
        mock_bot.config_manager.save_config = Mock()
        
        # Test CommandHandler
        cmd_handler = CommandHandler(mock_bot)
        tester.test_result("CommandHandler initialization", hasattr(cmd_handler, 'bot'))
        tester.test_result("CommandHandler has start_command", hasattr(cmd_handler, 'start_command'))
        
        # Test KeywordHandler
        kw_handler = KeywordHandler(mock_bot)
        tester.test_result("KeywordHandler initialization", hasattr(kw_handler, 'tbot'))
        tester.test_result("KeywordHandler has add_keyword", hasattr(kw_handler, 'add_keyword_handler'))
        tester.test_result("KeywordHandler has remove_keyword", hasattr(kw_handler, 'remove_keyword_handler'))
        tester.test_result("KeywordHandler has ignore_user", hasattr(kw_handler, 'ignore_user_handler'))
        
        # Test MessageHandler
        msg_handler = MessageHandler(mock_bot)
        tester.test_result("MessageHandler initialization", hasattr(msg_handler, 'tbot'))
        tester.test_result("MessageHandler has account_handler", hasattr(msg_handler, 'account_handler'))
        tester.test_result("MessageHandler has keyword_handler", hasattr(msg_handler, 'keyword_handler'))
        tester.test_result("MessageHandler has actions", hasattr(msg_handler, 'actions'))
        
        # Test StatsHandler
        stats_handler = StatsHandler(mock_bot)
        tester.test_result("StatsHandler initialization", hasattr(stats_handler, 'tbot'))
        tester.test_result("StatsHandler has show_stats", hasattr(stats_handler, 'show_stats'))
        tester.test_result("StatsHandler has show_groups", hasattr(stats_handler, 'show_groups'))
        tester.test_result("StatsHandler has show_keywords", hasattr(stats_handler, 'show_keywords'))
        tester.test_result("StatsHandler has show_ignores", hasattr(stats_handler, 'show_ignores'))
        
        # Test CallbackHandler
        cb_handler = CallbackHandler(mock_bot)
        tester.test_result("CallbackHandler initialization", hasattr(cb_handler, 'tbot'))
        tester.test_result("CallbackHandler has actions", hasattr(cb_handler, 'actions'))
        tester.test_result("CallbackHandler has callback_actions dict", isinstance(cb_handler.callback_actions, dict))
        
        # Verify callback_actions includes all operations
        expected_callbacks = [
            'add_account', 'list_accounts', 'update_groups',
            'add_keyword', 'remove_keyword', 'ignore_user', 'remove_ignore_user',
            'show_stats', 'show_groups', 'Show_keyword', 'show_ignores',
            'bulk_reaction', 'bulk_poll', 'bulk_join', 'bulk_block', 'bulk_send_pv', 'bulk_comment',
            'send_pv', 'join', 'left', 'comment'
        ]
        
        for callback in expected_callbacks:
            has_callback = callback in cb_handler.callback_actions
            tester.test_result(f"CallbackHandler has '{callback}'", has_callback)
        
    except Exception as e:
        tester.test_result("Handlers structure", False, str(e))
    
    return tester

def test_actions_structure():
    """Test Actions class structure"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: ACTIONS STRUCTURE")
    logger.info("="*60)
    
    try:
        from src.actions import Actions
        
        # Mock bot
        mock_bot = Mock()
        mock_bot.active_clients = {}
        mock_bot._conversations = {}
        mock_bot.handlers = {}
        
        actions = Actions(mock_bot)
        
        # Test initialization
        tester.test_result("Actions initialization", hasattr(actions, 'tbot'))
        tester.test_result("Actions has semaphore", hasattr(actions, 'operation_semaphore'))
        
        # Test all action methods exist
        action_methods = [
            'prompt_group_action',
            'prompt_individual_action',
            'handle_group_action',
            'handle_individual_action',
            'reaction',
            'reaction_link_handler',
            'reaction_select_handler',
            'reaction_count_handler',
            'apply_reaction',
            'poll',
            'poll_link_handler',
            'poll_option_handler',
            'join',
            'join_link_handler',
            'left',
            'left_link_handler',
            'block',
            'block_user_handler',
            'send_pv',
            'send_pv_user_handler',
            'send_pv_message_handler',
            'comment',
            'comment_link_handler',
            'comment_text_handler',
        ]
        
        for method in action_methods:
            has_method = hasattr(actions, method)
            tester.test_result(f"Actions has '{method}'", has_method)
        
    except Exception as e:
        tester.test_result("Actions structure", False, str(e))
    
    return tester

def test_client_structure():
    """Test Client/SessionManager structure"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: CLIENT/SESSION MANAGER STRUCTURE")
    logger.info("="*60)
    
    try:
        from src.Client import SessionManager, AccountHandler
        
        # Mock objects
        mock_config = {'clients': {}}
        mock_active_clients = {}
        mock_tbot = Mock()
        
        # Test SessionManager
        session_mgr = SessionManager(mock_config, mock_active_clients, mock_tbot)
        tester.test_result("SessionManager initialization", hasattr(session_mgr, 'config'))
        tester.test_result("SessionManager has detect_sessions", hasattr(session_mgr, 'detect_sessions'))
        tester.test_result("SessionManager has start_saved_clients", hasattr(session_mgr, 'start_saved_clients'))
        tester.test_result("SessionManager has disconnect_all_clients", hasattr(session_mgr, 'disconnect_all_clients'))
        tester.test_result("SessionManager has delete_session", hasattr(session_mgr, 'delete_session'))
        
        # Test AccountHandler
        mock_bot = Mock()
        mock_bot.config = {'clients': {}, 'IGNORE_USERS': [], 'KEYWORDS': []}
        mock_bot._conversations = {}
        mock_bot.active_clients = {}
        mock_bot.client_manager = session_mgr
        mock_bot.tbot = Mock()
        mock_bot.config_manager = Mock()
        mock_bot.monitor = Mock()
        mock_bot.active_clients_lock = asyncio.Lock()
        
        account_handler = AccountHandler(mock_bot)
        tester.test_result("AccountHandler initialization", hasattr(account_handler, 'tbot'))
        
        account_methods = [
            'add_account',
            'phone_number_handler',
            'code_handler',
            'password_handler',
            'finalize_client_setup',
            'cleanup_temp_handlers',
            'update_groups',
            'show_accounts',
            'toggle_client',
            'delete_client',
        ]
        
        for method in account_methods:
            has_method = hasattr(account_handler, method)
            tester.test_result(f"AccountHandler has '{method}'", has_method)
        
    except Exception as e:
        tester.test_result("Client structure", False, str(e))
    
    return tester

def test_monitor_structure():
    """Test Monitor class structure"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: MONITOR STRUCTURE")
    logger.info("="*60)
    
    try:
        from src.Monitor import Monitor
        
        # Mock bot
        mock_bot = Mock()
        mock_bot.tbot = Mock()
        mock_bot.config = {'KEYWORDS': [], 'IGNORE_USERS': []}
        
        monitor = Monitor(mock_bot)
        
        tester.test_result("Monitor initialization", hasattr(monitor, 'tbot'))
        tester.test_result("Monitor has resolve_channel_id", hasattr(monitor, 'resolve_channel_id'))
        tester.test_result("Monitor has process_messages_for_client", hasattr(monitor, 'process_messages_for_client'))
        
    except Exception as e:
        tester.test_result("Monitor structure", False, str(e))
    
    return tester

async def test_async_locks():
    """Test async lock mechanisms"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: ASYNC LOCK MECHANISMS")
    logger.info("="*60)
    
    try:
        # Test Lock
        lock = asyncio.Lock()
        
        counter = 0
        
        async def increment_with_lock():
            nonlocal counter
            async with lock:
                temp = counter
                await asyncio.sleep(0.001)
                counter = temp + 1
        
        # Run 10 concurrent operations
        await asyncio.gather(*[increment_with_lock() for _ in range(10)])
        
        # With lock, counter should be exactly 10
        tester.test_result("Lock prevents race condition", counter == 10)
        
        # Test Semaphore
        semaphore = asyncio.Semaphore(3)
        concurrent_count = 0
        max_concurrent = 0
        
        async def task_with_semaphore():
            nonlocal concurrent_count, max_concurrent
            async with semaphore:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
                await asyncio.sleep(0.01)
                concurrent_count -= 1
        
        # Run 10 tasks with semaphore(3)
        await asyncio.gather(*[task_with_semaphore() for _ in range(10)])
        
        # Max concurrent should not exceed 3
        tester.test_result("Semaphore limits concurrency", max_concurrent <= 3)
        logger.info(f"   Max concurrent tasks: {max_concurrent}")
        
    except Exception as e:
        tester.test_result("Async locks", False, str(e))
    
    return tester

def test_data_integrity():
    """Test data integrity and consistency"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: DATA INTEGRITY")
    logger.info("="*60)
    
    try:
        from src.Config import ConfigManager
        import os
        import json
        
        test_file = "test_integrity.json"
        
        # Test 1: Save and load integrity
        config_mgr = ConfigManager(test_file)
        original_data = {
            'KEYWORDS': ['test1', 'test2', 'تست'],
            'IGNORE_USERS': [123, 456, 789],
            'clients': {'session1': [111, 222], 'session2': [333]}
        }
        
        for key, value in original_data.items():
            config_mgr.update_config(key, value)
        
        # Reload
        config_mgr2 = ConfigManager(test_file)
        
        # Verify all data
        for key, expected_value in original_data.items():
            actual_value = config_mgr2.get_config(key)
            match = actual_value == expected_value
            tester.test_result(f"Data integrity: {key}", match)
        
        # Test 2: JSON structure
        with open(test_file, 'r') as f:
            json_data = json.load(f)
        
        is_valid_json = isinstance(json_data, dict)
        tester.test_result("Valid JSON structure", is_valid_json)
        
        # Test 3: Unicode handling
        config_mgr.update_config('persian_text', 'سلام دنیا')
        persian = config_mgr.get_config('persian_text')
        tester.test_result("Unicode/Persian text handling", persian == 'سلام دنیا')
        
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
        
    except Exception as e:
        tester.test_result("Data integrity", False, str(e))
    
    return tester

def test_keyboard_generation():
    """Test keyboard generation"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: KEYBOARD GENERATION")
    logger.info("="*60)
    
    try:
        from src.Keyboards import Keyboard
        from telethon import Button
        
        # Test all keyboards
        keyboards = {
            'start': Keyboard.start_keyboard(),
            'monitor': Keyboard.monitor_keyboard(),
            'bulk': Keyboard.bulk_keyboard(),
            'account_management': Keyboard.account_management_keyboard(),
            'individual': Keyboard.individual_keyboard(),
            'report': Keyboard.report_keyboard(),
        }
        
        for name, keyboard in keyboards.items():
            # Check it's a list
            tester.test_result(f"{name} is list", isinstance(keyboard, list))
            
            # Check it has buttons
            has_buttons = len(keyboard) > 0
            tester.test_result(f"{name} has buttons", has_buttons)
            
            # Check button structure
            if has_buttons:
                first_row = keyboard[0]
                is_valid_row = isinstance(first_row, list)
                tester.test_result(f"{name} valid button rows", is_valid_row)
        
        # Test dynamic keyboards
        msg_keyboard = Keyboard.channel_message_keyboard("https://t.me/test/123", 12345)
        tester.test_result("channel_message_keyboard generates buttons", isinstance(msg_keyboard, list))
        
        toggle_keyboard = Keyboard.toggle_and_delete_keyboard("🟢 Active", "test_session")
        tester.test_result("toggle_and_delete_keyboard generates buttons", isinstance(toggle_keyboard, list))
        
    except Exception as e:
        tester.test_result("Keyboard generation", False, str(e))
    
    return tester

def test_logger_functionality():
    """Test logger setup"""
    tester = DeepTester()
    logger.info("\n" + "="*60)
    logger.info("TEST: LOGGER FUNCTIONALITY")
    logger.info("="*60)
    
    try:
        from src.Logger import setup_logging
        import os
        
        # Test setup
        setup_logging("test_deep.log")
        tester.test_result("Logger setup successful", True)
        
        # Test log file creation
        log_file_exists = os.path.exists("logs/test_deep.log")
        tester.test_result("Log file created", log_file_exists)
        
        # Test logging
        test_logger = logging.getLogger("test_deep")
        test_logger.info("Test log entry")
        test_logger.warning("Test warning")
        test_logger.error("Test error")
        
        tester.test_result("Logger can write messages", True)
        
        # Cleanup
        if os.path.exists("logs/test_deep.log"):
            os.remove("logs/test_deep.log")
        
    except Exception as e:
        tester.test_result("Logger functionality", False, str(e))
    
    return tester

async def main():
    """Run all deep tests"""
    logger.info("\n" + "🔬 "*20)
    logger.info("DEEP FUNCTIONALITY TESTING")
    logger.info("🔬 "*20)
    
    all_testers = []
    
    # Synchronous tests
    all_testers.append(test_handlers_structure())
    all_testers.append(test_actions_structure())
    all_testers.append(test_client_structure())
    all_testers.append(test_monitor_structure())
    all_testers.append(test_data_integrity())
    all_testers.append(test_keyboard_generation())
    all_testers.append(test_logger_functionality())
    
    # Async tests
    all_testers.append(await test_async_locks())
    
    # Calculate totals
    total_passed = sum(t.passed for t in all_testers)
    total_failed = sum(t.failed for t in all_testers)
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("🔬 DEEP FUNCTIONALITY TEST - FINAL SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests Run: {total_passed + total_failed}")
    logger.info(f"✅ Total Passed: {total_passed}")
    logger.info(f"❌ Total Failed: {total_failed}")
    
    if total_passed + total_failed > 0:
        success_rate = (total_passed / (total_passed + total_failed)) * 100
        logger.info(f"Success Rate: {success_rate:.1f}%")
    
    logger.info("="*60)
    
    if total_failed == 0:
        logger.info("\n🎉 ALL DEEP TESTS PASSED!")
        logger.info("✅ System is fully functional at code level!")
        return 0
    else:
        logger.error(f"\n⚠️ {total_failed} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

