#!/usr/bin/env python3
"""
Interactive Bot Testing Script
Tests bot functionality without needing manual interaction
"""

import asyncio
import logging
from telethon import TelegramClient, events
from src.Config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class BotTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.bot_username = None
        
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

async def test_bot_connection():
    """Test bot connection and basic info"""
    tester = BotTester()
    logger.info("\n" + "="*60)
    logger.info("BOT INTERACTION TEST")
    logger.info("="*60)
    
    try:
        # Create client for testing
        client = TelegramClient('test_client', API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
        
        # Test 1: Get bot info
        logger.info("\nTEST 1: Bot Information")
        me = await client.get_me()
        tester.test_result("Get bot information", me is not None)
        
        if me:
            logger.info(f"  Bot Username: @{me.username}")
            logger.info(f"  Bot ID: {me.id}")
            logger.info(f"  Bot Name: {me.first_name}")
            tester.bot_username = me.username
        
        # Test 2: Check if bot is actually a bot
        logger.info("\nTEST 2: Verify Bot Type")
        is_bot = me.bot if me else False
        tester.test_result("Is bot account", is_bot)
        
        # Test 3: Test bot connectivity
        logger.info("\nTEST 3: Bot Connectivity")
        is_connected = client.is_connected()
        tester.test_result("Bot connected", is_connected)
        
        # Test 4: Test admin ID validity
        logger.info("\nTEST 4: Admin Configuration")
        try:
            admin_id_valid = isinstance(ADMIN_ID, int) and ADMIN_ID > 0
            tester.test_result("Admin ID valid", admin_id_valid)
            if admin_id_valid:
                logger.info(f"  Admin ID: {ADMIN_ID}")
        except:
            tester.test_result("Admin ID valid", False, "Invalid admin ID")
        
        # Test 5: Send test message to self (if possible)
        logger.info("\nTEST 5: Message Sending")
        try:
            # Try to send a message to the admin
            test_msg = "🤖 Bot Test - Connection Successful!\n\n✅ Bot is working properly."
            await client.send_message(ADMIN_ID, test_msg)
            tester.test_result("Send message to admin", True)
            logger.info("  ✅ Test message sent to admin successfully")
        except Exception as e:
            tester.test_result("Send message to admin", False, str(e))
        
        # Test 6: Verify bot can receive commands
        logger.info("\nTEST 6: Command Reception")
        
        # Set up a simple command handler
        received_command = False
        
        @client.on(events.NewMessage(pattern='/test'))
        async def test_handler(event):
            nonlocal received_command
            received_command = True
            await event.respond("Test command received!")
        
        # Simulate sending /test command from admin
        try:
            await client.send_message(tester.bot_username, '/test')
            await asyncio.sleep(2)  # Wait for response
            tester.test_result("Command reception", received_command)
        except Exception as e:
            tester.test_result("Command reception", False, str(e))
        
        # Cleanup
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"Critical error in testing: {e}")
        tester.test_result("Bot connection test", False, str(e))
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("BOT TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests: {tester.passed + tester.failed}")
    logger.info(f"✅ Passed: {tester.passed}")
    logger.info(f"❌ Failed: {tester.failed}")
    
    if tester.errors:
        logger.info("\nERRORS:")
        for error in tester.errors:
            logger.error(f"  - {error}")
    
    logger.info("="*60)
    
    return tester.failed == 0

async def test_validation_module():
    """Test validation module in detail"""
    logger.info("\n" + "="*60)
    logger.info("VALIDATION MODULE DEEP TEST")
    logger.info("="*60)
    
    from src.Validation import InputValidator
    
    tester = BotTester()
    
    # Test edge cases
    test_cases = [
        # Phone numbers
        (InputValidator.validate_phone_number, "+989121234567", True, "Valid Iranian phone"),
        (InputValidator.validate_phone_number, "+1234567890", True, "Valid international phone"),
        (InputValidator.validate_phone_number, "09121234567", False, "Missing + prefix"),
        (InputValidator.validate_phone_number, "+12345", False, "Too short"),
        (InputValidator.validate_phone_number, "+123456789012345678", False, "Too long"),
        (InputValidator.validate_phone_number, "+12345abc890", False, "Contains letters"),
        
        # User IDs
        (lambda x: InputValidator.validate_user_id(x)[:2], "123456789", (True, None), "Valid user ID"),
        (lambda x: InputValidator.validate_user_id(x)[:2], "0", (False, None), "Zero ID"),
        (lambda x: InputValidator.validate_user_id(x)[:2], "-123", (False, None), "Negative ID"),
        (lambda x: InputValidator.validate_user_id(x)[:2], "abc123", (False, None), "Letters in ID"),
        
        # Keywords
        (InputValidator.validate_keyword, "test", True, "Valid 2-char keyword"),
        (InputValidator.validate_keyword, "سلام", True, "Valid Persian keyword"),
        (InputValidator.validate_keyword, "a", False, "Single character"),
        (InputValidator.validate_keyword, "", False, "Empty keyword"),
        (InputValidator.validate_keyword, " ", False, "Whitespace only"),
        
        # Telegram links
        (InputValidator.validate_telegram_link, "https://t.me/channel", True, "HTTPS link"),
        (InputValidator.validate_telegram_link, "http://t.me/channel", True, "HTTP link"),
        (InputValidator.validate_telegram_link, "t.me/channel", False, "Missing protocol"),
        (InputValidator.validate_telegram_link, "@username", True, "Username with @"),
        (InputValidator.validate_telegram_link, "username", True, "Plain username"),
        
        # Messages
        (InputValidator.validate_message_text, "Hello", True, "Simple message"),
        (InputValidator.validate_message_text, "سلام دنیا", True, "Persian message"),
        (InputValidator.validate_message_text, "", False, "Empty message"),
        (InputValidator.validate_message_text, "a" * 4096, True, "Max length message"),
        (InputValidator.validate_message_text, "a" * 4097, False, "Over max length"),
    ]
    
    for func, input_val, expected, description in test_cases:
        try:
            result = func(input_val)
            # Extract boolean from result (could be tuple or just bool)
            if isinstance(result, tuple):
                success = result[0] == expected[0] if isinstance(expected, tuple) else result[0] == expected
            else:
                success = result == expected
            
            tester.test_result(description, success)
        except Exception as e:
            tester.test_result(description, False, str(e))
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("VALIDATION TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests: {tester.passed + tester.failed}")
    logger.info(f"✅ Passed: {tester.passed}")
    logger.info(f"❌ Failed: {tester.failed}")
    logger.info("="*60)
    
    return tester.failed == 0

async def test_config_management():
    """Test configuration management"""
    logger.info("\n" + "="*60)
    logger.info("CONFIG MANAGEMENT DEEP TEST")
    logger.info("="*60)
    
    from src.Config import ConfigManager
    import os
    
    tester = BotTester()
    
    # Create test config
    test_config_path = "test_deep_config.json"
    
    try:
        # Test 1: Create new config
        config_mgr = ConfigManager(test_config_path)
        tester.test_result("Create config manager", True)
        
        # Test 2: Get default config
        config = config_mgr.get_config()
        has_keys = all(k in config for k in ['TARGET_GROUPS', 'KEYWORDS', 'IGNORE_USERS', 'clients'])
        tester.test_result("Config has all default keys", has_keys)
        
        # Test 3: Update simple value
        config_mgr.update_config('test_value', 12345)
        retrieved = config_mgr.get_config('test_value')
        tester.test_result("Update and retrieve value", retrieved == 12345)
        
        # Test 4: Update list value
        config_mgr.update_config('KEYWORDS', ['test', 'keyword'])
        keywords = config_mgr.get_config('KEYWORDS')
        tester.test_result("Update list value", keywords == ['test', 'keyword'])
        
        # Test 5: Merge config
        config_mgr.merge_config({'KEYWORDS': ['new'], 'test_key': 'test_value'})
        merged_keywords = config_mgr.get_config('KEYWORDS')
        tester.test_result("Merge config (list dedup)", 'test' in merged_keywords and 'new' in merged_keywords)
        
        # Test 6: Persistence
        config_mgr2 = ConfigManager(test_config_path)
        persisted_value = config_mgr2.get_config('test_value')
        tester.test_result("Config persistence", persisted_value == 12345)
        
        # Cleanup
        if os.path.exists(test_config_path):
            os.remove(test_config_path)
            
    except Exception as e:
        tester.test_result("Config management", False, str(e))
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("CONFIG TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests: {tester.passed + tester.failed}")
    logger.info(f"✅ Passed: {tester.passed}")
    logger.info(f"❌ Failed: {tester.failed}")
    logger.info("="*60)
    
    return tester.failed == 0

async def main():
    """Run all deep tests"""
    logger.info("\n" + "🚀 "*20)
    logger.info("COMPREHENSIVE BOT DEEP TESTING")
    logger.info("🚀 "*20)
    
    results = []
    
    # Run bot connection test
    try:
        result = await test_bot_connection()
        results.append(("Bot Connection", result))
    except Exception as e:
        logger.error(f"Bot connection test failed: {e}")
        results.append(("Bot Connection", False))
    
    # Run validation test
    try:
        result = await test_validation_module()
        results.append(("Validation Module", result))
    except Exception as e:
        logger.error(f"Validation test failed: {e}")
        results.append(("Validation Module", False))
    
    # Run config test
    try:
        result = await test_config_management()
        results.append(("Config Management", result))
    except Exception as e:
        logger.error(f"Config test failed: {e}")
        results.append(("Config Management", False))
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("FINAL COMPREHENSIVE TEST SUMMARY")
    logger.info("="*60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(r[1] for r in results)
    logger.info("="*60)
    
    if all_passed:
        logger.info("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        logger.info("✅ Bot is fully functional and ready for use!")
        return 0
    else:
        logger.error("\n⚠️ Some tests failed. Please review errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

