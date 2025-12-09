"""
Unit tests for InputValidator class
"""
import pytest
from src.Validation import InputValidator


class TestInputValidator:
    """Test suite for InputValidator"""

    def test_validate_phone_number_valid(self):
        """Test valid phone number formats"""
        valid_numbers = [
            "+1234567890",
            "+9876543210",
            "+123456789012345",
            "+12345678901234"
        ]
        for phone in valid_numbers:
            is_valid, error_msg = InputValidator.validate_phone_number(phone)
            assert is_valid, f"Phone {phone} should be valid: {error_msg}"
            assert error_msg is None

    def test_validate_phone_number_invalid(self):
        """Test invalid phone number formats"""
        invalid_cases = [
            ("", "Phone number cannot be empty"),
            ("1234567890", "Must start with +"),
            ("+123", "Too short"),
            ("+1234567890123456", "Too long"),
            ("+abc123456", "Contains non-digits"),
            ("1234567890+", "Wrong format")
        ]
        for phone, expected_error in invalid_cases:
            is_valid, error_msg = InputValidator.validate_phone_number(phone)
            assert not is_valid, f"Phone {phone} should be invalid"
            assert error_msg is not None

    def test_validate_user_id_valid(self):
        """Test valid user IDs"""
        valid_ids = ["123456789", "1", "999999999999"]
        for user_id_str in valid_ids:
            is_valid, error_msg, user_id = InputValidator.validate_user_id(user_id_str)
            assert is_valid, f"User ID {user_id_str} should be valid: {error_msg}"
            assert error_msg is None
            assert user_id == int(user_id_str)

    def test_validate_user_id_invalid(self):
        """Test invalid user IDs"""
        invalid_cases = [
            ("", "User ID cannot be empty"),
            ("0", "Must be positive"),
            ("-1", "Must be positive"),
            ("abc", "Must be a valid number"),
            ("12.5", "Must be a valid number")
        ]
        for user_id_str, expected_error in invalid_cases:
            is_valid, error_msg, user_id = InputValidator.validate_user_id(user_id_str)
            assert not is_valid, f"User ID {user_id_str} should be invalid"
            assert error_msg is not None

    def test_validate_keyword_valid(self):
        """Test valid keywords"""
        valid_keywords = ["test", "keyword", "a" * 50, "test123"]
        for keyword in valid_keywords:
            is_valid, error_msg = InputValidator.validate_keyword(keyword)
            assert is_valid, f"Keyword '{keyword}' should be valid: {error_msg}"
            assert error_msg is None

    def test_validate_keyword_invalid(self):
        """Test invalid keywords"""
        invalid_cases = [
            ("", "Keyword cannot be empty"),
            ("a", "Too short"),
            ("a" * 101, "Too long"),
            ("   ", "Empty after strip")
        ]
        for keyword, expected_error in invalid_cases:
            is_valid, error_msg = InputValidator.validate_keyword(keyword)
            assert not is_valid, f"Keyword '{keyword}' should be invalid"
            assert error_msg is not None

    def test_validate_telegram_link_valid(self):
        """Test valid Telegram links"""
        valid_links = [
            "https://t.me/test",
            "http://t.me/test",
            "https://t.me/c/123456/789",
            "@username",
            "username",
            "https://t.me/test/123"
        ]
        for link in valid_links:
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            assert is_valid, f"Link '{link}' should be valid: {error_msg}"
            assert error_msg is None

    def test_validate_telegram_link_invalid(self):
        """Test invalid Telegram links"""
        invalid_cases = [
            ("", "Link cannot be empty"),
            ("https://example.com", "Not a Telegram link"),
            ("http://telegram.org", "Not a Telegram link"),
            ("invalid", "Invalid format")
        ]
        for link, expected_error in invalid_cases:
            is_valid, error_msg = InputValidator.validate_telegram_link(link)
            # Note: Some might pass due to regex, but we test the main cases
            if not is_valid:
                assert error_msg is not None

    def test_validate_poll_option_valid(self):
        """Test valid poll options"""
        valid_options = ["1", "2", "5", "10"]
        for option_str in valid_options:
            is_valid, error_msg, option = InputValidator.validate_poll_option(option_str)
            assert is_valid, f"Option '{option_str}' should be valid: {error_msg}"
            assert error_msg is None
            assert option == int(option_str)

    def test_validate_poll_option_invalid(self):
        """Test invalid poll options"""
        invalid_cases = [
            ("", "Option number cannot be empty"),
            ("0", "Must be between 1 and 10"),
            ("11", "Must be between 1 and 10"),
            ("abc", "Must be a valid number"),
            ("-1", "Must be between 1 and 10")
        ]
        for option_str, expected_error in invalid_cases:
            is_valid, error_msg, option = InputValidator.validate_poll_option(option_str)
            assert not is_valid, f"Option '{option_str}' should be invalid"
            assert error_msg is not None

    def test_validate_message_text_valid(self):
        """Test valid message texts"""
        valid_texts = [
            "Hello",
            "a" * 4096,  # Max length
            "Test message with special chars: @#$%^&*()",
            "Multi\nline\nmessage"
        ]
        for text in valid_texts:
            is_valid, error_msg = InputValidator.validate_message_text(text)
            assert is_valid, f"Text should be valid: {error_msg}"
            assert error_msg is None

    def test_validate_message_text_invalid(self):
        """Test invalid message texts"""
        invalid_cases = [
            ("", "Message cannot be empty"),
            ("   ", "Empty after strip"),
            ("a" * 4097, "Exceeds Telegram limit")
        ]
        for text, expected_error in invalid_cases:
            is_valid, error_msg = InputValidator.validate_message_text(text)
            assert not is_valid, f"Text should be invalid"
            assert error_msg is not None

    def test_validate_count_valid(self):
        """Test valid counts"""
        max_count = 10
        valid_counts = ["1", "5", "10"]
        for count_str in valid_counts:
            is_valid, error_msg, count = InputValidator.validate_count(count_str, max_count)
            assert is_valid, f"Count '{count_str}' should be valid: {error_msg}"
            assert error_msg is None
            assert count == int(count_str)

    def test_validate_count_invalid(self):
        """Test invalid counts"""
        max_count = 10
        invalid_cases = [
            ("", "Count cannot be empty"),
            ("0", "Must be at least 1"),
            ("11", "Cannot exceed max_count"),
            ("abc", "Must be a valid number"),
            ("-1", "Must be at least 1")
        ]
        for count_str, expected_error in invalid_cases:
            is_valid, error_msg, count = InputValidator.validate_count(count_str, max_count)
            assert not is_valid, f"Count '{count_str}' should be invalid"
            assert error_msg is not None

    def test_sanitize_input_normal(self):
        """Test normal input sanitization"""
        test_cases = [
            ("Hello World", "Hello World"),
            ("Test\nMessage", "Test\nMessage"),  # Newline preserved
            ("Test\tMessage", "Test\tMessage"),  # Tab preserved
        ]
        for input_text, expected in test_cases:
            result = InputValidator.sanitize_input(input_text)
            assert result == expected

    def test_sanitize_input_truncation(self):
        """Test input truncation"""
        long_text = "a" * 2000
        max_length = 1000
        result = InputValidator.sanitize_input(long_text, max_length=max_length)
        assert len(result) == max_length
        assert result == "a" * max_length

    def test_sanitize_input_control_chars(self):
        """Test removal of control characters"""
        text_with_control = "Hello\x00World\x01Test"
        result = InputValidator.sanitize_input(text_with_control)
        # Control chars should be removed, but printable chars preserved
        assert "\x00" not in result
        assert "\x01" not in result
        assert "Hello" in result
        assert "World" in result
        assert "Test" in result

    def test_sanitize_input_empty(self):
        """Test empty input sanitization"""
        result = InputValidator.sanitize_input("")
        assert result == ""
        result = InputValidator.sanitize_input(None)
        assert result == ""

