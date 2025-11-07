#!/usr/bin/env python3
"""
Comprehensive System Test Suite
Tests all components and functionality
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Setup logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class SystemTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def test_result(self, test_name, success, error_msg=None):
        """Record test result"""
        if success:
            self.passed += 1
            logger.info(f"✅ PASS: {test_name}")
        else:
            self.failed += 1
            logger.error(f"❌ FAIL: {test_name}")
            if error_msg:
                logger.error(f"   Error: {error_msg}")
                self.errors.append(f"{test_name}: {error_msg}")
    
    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {self.passed}")
        logger.info(f"❌ Failed: {self.failed}")
        logger.info(f"Success Rate: {(self.passed/total*100) if total > 0 else 0:.1f}%")
        
        if self.errors:
            logger.info("\n" + "="*60)
            logger.info("ERRORS:")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        logger.info("="*60)
        return self.failed == 0

def test_imports():
    """Test 1: Import all modules"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Module Imports")
    logger.info("="*60)
    
    modules = [
        'src.Config',
        'src.Logger',
        'src.Telbot',
        'src.Client',
        'src.Handlers',
        'src.Keyboards',
        'src.Monitor',
        'src.actions',
        'src.Validation',
    ]
    
    for module in modules:
        try:
            __import__(module)
            tester.test_result(f"Import {module}", True)
        except Exception as e:
            tester.test_result(f"Import {module}", False, str(e))
    
    return tester

def test_validation():
    """Test 2: Validation Functions"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Validation Functions")
    logger.info("="*60)
    
    try:
        from src.Validation import InputValidator
        
        # Test phone number validation
        valid, err = InputValidator.validate_phone_number("+1234567890")
        tester.test_result("Valid phone number", valid and err is None)
        
        valid, err = InputValidator.validate_phone_number("1234567890")
        tester.test_result("Invalid phone (no +)", not valid and err is not None)
        
        valid, err = InputValidator.validate_phone_number("+12345")
        tester.test_result("Invalid phone (too short)", not valid and err is not None)
        
        # Test user ID validation
        valid, err, uid = InputValidator.validate_user_id("123456")
        tester.test_result("Valid user ID", valid and uid == 123456)
        
        valid, err, uid = InputValidator.validate_user_id("-123")
        tester.test_result("Invalid user ID (negative)", not valid)
        
        valid, err, uid = InputValidator.validate_user_id("abc")
        tester.test_result("Invalid user ID (non-numeric)", not valid)
        
        # Test keyword validation
        valid, err = InputValidator.validate_keyword("test")
        tester.test_result("Valid keyword", valid)
        
        valid, err = InputValidator.validate_keyword("a")
        tester.test_result("Invalid keyword (too short)", not valid)
        
        valid, err = InputValidator.validate_keyword("a" * 101)
        tester.test_result("Invalid keyword (too long)", not valid)
        
        # Test Telegram link validation
        valid, err = InputValidator.validate_telegram_link("https://t.me/username")
        tester.test_result("Valid Telegram link (https)", valid)
        
        valid, err = InputValidator.validate_telegram_link("@username")
        tester.test_result("Valid Telegram link (@)", valid)
        
        valid, err = InputValidator.validate_telegram_link("username")
        tester.test_result("Valid Telegram link (plain)", valid)
        
        valid, err = InputValidator.validate_telegram_link("invalid link!")
        tester.test_result("Invalid Telegram link", not valid)
        
        # Test message validation
        valid, err = InputValidator.validate_message_text("Hello World")
        tester.test_result("Valid message", valid)
        
        valid, err = InputValidator.validate_message_text("")
        tester.test_result("Invalid message (empty)", not valid)
        
        valid, err = InputValidator.validate_message_text("a" * 5000)
        tester.test_result("Invalid message (too long)", not valid)
        
        # Test count validation
        valid, err, count = InputValidator.validate_count("5", 10)
        tester.test_result("Valid count", valid and count == 5)
        
        valid, err, count = InputValidator.validate_count("15", 10)
        tester.test_result("Invalid count (exceeds max)", not valid)
        
        # Test sanitize
        sanitized = InputValidator.sanitize_input("Hello\x00World")
        tester.test_result("Sanitize removes control chars", "\x00" not in sanitized)
        
    except Exception as e:
        tester.test_result("Validation module", False, str(e))
    
    return tester

def test_config():
    """Test 3: Configuration Loading"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Configuration Loading")
    logger.info("="*60)
    
    try:
        from src.Config import ConfigManager, get_env_variable
        
        # Test ConfigManager initialization
        config_mgr = ConfigManager("test_config.json")
        tester.test_result("ConfigManager initialization", True)
        
        # Test default config structure
        config = config_mgr.get_config()
        required_keys = ['TARGET_GROUPS', 'KEYWORDS', 'IGNORE_USERS', 'clients']
        has_all_keys = all(key in config for key in required_keys)
        tester.test_result("Config has required keys", has_all_keys)
        
        # Test update config
        config_mgr.update_config('test_key', 'test_value')
        updated_value = config_mgr.get_config('test_key')
        tester.test_result("Update config", updated_value == 'test_value')
        
        # Cleanup test file
        if os.path.exists("test_config.json"):
            os.remove("test_config.json")
        
    except Exception as e:
        tester.test_result("Configuration", False, str(e))
    
    return tester

def test_keyboards():
    """Test 4: Keyboard Layouts"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Keyboard Layouts")
    logger.info("="*60)
    
    try:
        from src.Keyboards import Keyboard
        
        # Test all keyboard methods
        keyboards = {
            'start_keyboard': Keyboard.start_keyboard(),
            'monitor_keyboard': Keyboard.monitor_keyboard(),
            'bulk_keyboard': Keyboard.bulk_keyboard(),
            'account_management_keyboard': Keyboard.account_management_keyboard(),
            'individual_keyboard': Keyboard.individual_keyboard(),
            'report_keyboard': Keyboard.report_keyboard(),
        }
        
        for name, keyboard in keyboards.items():
            has_buttons = isinstance(keyboard, list) and len(keyboard) > 0
            tester.test_result(f"Keyboard: {name}", has_buttons)
        
        # Test channel_message_keyboard
        buttons = Keyboard.channel_message_keyboard("https://t.me/test/123", 12345)
        tester.test_result("Channel message keyboard", isinstance(buttons, list))
        
        # Test toggle_and_delete_keyboard
        buttons = Keyboard.toggle_and_delete_keyboard("🟢 Active", "test_session")
        tester.test_result("Toggle and delete keyboard", isinstance(buttons, list))
        
    except Exception as e:
        tester.test_result("Keyboards", False, str(e))
    
    return tester

def test_file_structure():
    """Test 5: File Structure"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 5: File Structure")
    logger.info("="*60)
    
    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        'env.example',
        '.gitignore',
        'src/Config.py',
        'src/Logger.py',
        'src/Telbot.py',
        'src/Client.py',
        'src/Handlers.py',
        'src/Keyboards.py',
        'src/Monitor.py',
        'src/actions.py',
        'src/Validation.py',
        'logs/',
    ]
    
    for file_path in required_files:
        exists = os.path.exists(file_path)
        tester.test_result(f"File exists: {file_path}", exists)
    
    return tester

def test_dependencies():
    """Test 6: Dependencies"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Dependencies Check")
    logger.info("="*60)
    
    dependencies = [
        ('telethon', 'Telethon'),
        ('dotenv', 'python-dotenv'),
        ('aiohttp', 'aiohttp'),
    ]
    
    for module, name in dependencies:
        try:
            __import__(module)
            tester.test_result(f"Dependency: {name}", True)
        except ImportError:
            tester.test_result(f"Dependency: {name}", False, "Not installed")
    
    return tester

async def test_async_functionality():
    """Test 7: Async Functionality"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 7: Async Functionality")
    logger.info("="*60)
    
    try:
        # Test asyncio.Lock
        lock = asyncio.Lock()
        async with lock:
            tester.test_result("asyncio.Lock", True)
        
        # Test asyncio.Semaphore
        sem = asyncio.Semaphore(3)
        async with sem:
            tester.test_result("asyncio.Semaphore", True)
        
        # Test asyncio.gather with return_exceptions
        async def dummy_task(should_fail=False):
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        results = await asyncio.gather(
            dummy_task(False),
            dummy_task(True),
            return_exceptions=True
        )
        
        has_success = results[0] == "success"
        has_exception = isinstance(results[1], Exception)
        tester.test_result("asyncio.gather with exceptions", has_success and has_exception)
        
    except Exception as e:
        tester.test_result("Async functionality", False, str(e))
    
    return tester

def test_logging():
    """Test 8: Logging Setup"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 8: Logging Setup")
    logger.info("="*60)
    
    try:
        from src.Logger import setup_logging
        
        # Test logging setup
        setup_logging("test.log")
        test_logger = logging.getLogger("test")
        test_logger.info("Test log message")
        
        tester.test_result("Logging setup", True)
        
        # Check if log directory exists
        tester.test_result("Log directory exists", os.path.exists("logs"))
        
    except Exception as e:
        tester.test_result("Logging", False, str(e))
    
    return tester

def test_circular_imports():
    """Test 9: Circular Import Detection"""
    tester = SystemTester()
    logger.info("\n" + "="*60)
    logger.info("TEST 9: Circular Import Detection")
    logger.info("="*60)
    
    # Clear all imported modules
    modules_to_test = [
        'src.Config',
        'src.Logger',
        'src.Validation',
        'src.Keyboards',
        'src.actions',
        'src.Monitor',
        'src.Client',
        'src.Handlers',
        'src.Telbot',
    ]
    
    for module in modules_to_test:
        try:
            # Force reimport
            if module in sys.modules:
                del sys.modules[module]
            __import__(module)
            tester.test_result(f"No circular import: {module}", True)
        except ImportError as e:
            if "circular" in str(e).lower():
                tester.test_result(f"No circular import: {module}", False, str(e))
            else:
                # Other import errors are OK for this test
                tester.test_result(f"No circular import: {module}", True)
        except Exception as e:
            tester.test_result(f"No circular import: {module}", False, str(e))
    
    return tester

def main():
    """Main test runner"""
    logger.info("\n" + "="*60)
    logger.info("TELEGRAM PANEL - COMPREHENSIVE SYSTEM TEST")
    logger.info("="*60)
    
    all_testers = []
    
    # Run all tests
    all_testers.append(test_imports())
    all_testers.append(test_validation())
    all_testers.append(test_config())
    all_testers.append(test_keyboards())
    all_testers.append(test_file_structure())
    all_testers.append(test_dependencies())
    
    # Run async tests
    loop = asyncio.get_event_loop()
    all_testers.append(loop.run_until_complete(test_async_functionality()))
    
    all_testers.append(test_logging())
    all_testers.append(test_circular_imports())
    
    # Calculate totals
    total_passed = sum(t.passed for t in all_testers)
    total_failed = sum(t.failed for t in all_testers)
    all_errors = []
    for t in all_testers:
        all_errors.extend(t.errors)
    
    # Print final summary
    logger.info("\n" + "="*60)
    logger.info("FINAL TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests Run: {total_passed + total_failed}")
    logger.info(f"✅ Total Passed: {total_passed}")
    logger.info(f"❌ Total Failed: {total_failed}")
    
    if total_passed + total_failed > 0:
        success_rate = (total_passed / (total_passed + total_failed)) * 100
        logger.info(f"Success Rate: {success_rate:.1f}%")
    
    if all_errors:
        logger.info("\n" + "="*60)
        logger.info("ALL ERRORS:")
        for error in all_errors:
            logger.error(f"  - {error}")
    
    logger.info("="*60)
    
    if total_failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED! System is ready for production.")
        return 0
    else:
        logger.error(f"\n⚠️  {total_failed} test(s) failed. Please review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

