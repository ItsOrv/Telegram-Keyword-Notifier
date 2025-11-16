import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class InputValidator:
    """Validates user inputs to ensure data integrity and security"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate phone number format
        
        Args:
            phone: Phone number string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        phone = phone.strip()
        
        if not phone:
            return False, "Phone number cannot be empty"
        
        # Check if starts with + and contains only digits
        if not re.match(r'^\+\d{10,15}$', phone):
            return False, "Phone number must start with '+' and contain 10-15 digits (e.g., +1234567890)"
        
        return True, None
    
    @staticmethod
    def validate_user_id(user_id_str: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validate and parse user ID
        
        Args:
            user_id_str: User ID as string
            
        Returns:
            Tuple of (is_valid, error_message, parsed_id)
        """
        user_id_str = user_id_str.strip()
        
        if not user_id_str:
            return False, "User ID cannot be empty", None
        
        try:
            user_id = int(user_id_str)
            if user_id <= 0:
                return False, "User ID must be a positive number", None
            return True, None, user_id
        except ValueError:
            return False, "User ID must be a valid number", None
    
    @staticmethod
    def validate_keyword(keyword: str) -> Tuple[bool, Optional[str]]:
        """
        Validate keyword
        
        Args:
            keyword: Keyword string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        keyword = keyword.strip()
        
        if not keyword:
            return False, "Keyword cannot be empty"
        
        if len(keyword) < 2:
            return False, "Keyword must be at least 2 characters long"
        
        if len(keyword) > 100:
            return False, "Keyword cannot exceed 100 characters"
        
        return True, None
    
    @staticmethod
    def validate_telegram_link(link: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Telegram link format
        
        Args:
            link: Telegram link
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        link = link.strip()
        
        if not link:
            return False, "Link cannot be empty"
        
        # Check if it's a valid Telegram link or username
        telegram_patterns = [
            r'^https?://t\.me/[\w/-]+$',  # https://t.me/username or https://t.me/c/123/456
            r'^@[\w]+$',  # @username
            r'^[\w]+$',  # username
        ]
        
        if not any(re.match(pattern, link) for pattern in telegram_patterns):
            return False, "Invalid Telegram link. Use format: https://t.me/... or @username or username"
        
        return True, None
    
    @staticmethod
    def validate_poll_option(option_str: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validate poll option number
        
        Args:
            option_str: Option number as string
            
        Returns:
            Tuple of (is_valid, error_message, parsed_option)
        """
        option_str = option_str.strip()
        
        if not option_str:
            return False, "Option number cannot be empty", None
        
        try:
            option = int(option_str)
            if option < 1 or option > 10:
                return False, "Option number must be between 1 and 10", None
            return True, None, option
        except ValueError:
            return False, "Option must be a valid number", None
    
    @staticmethod
    def validate_message_text(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate message text
        
        Args:
            text: Message text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        text = text.strip()
        
        if not text:
            return False, "Message cannot be empty"
        
        if len(text) > 4096:
            return False, "Message cannot exceed 4096 characters (Telegram limit)"
        
        return True, None
    
    @staticmethod
    def validate_count(count_str: str, max_count: int) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validate account count for bulk operations
        
        Args:
            count_str: Count as string
            max_count: Maximum allowed count
            
        Returns:
            Tuple of (is_valid, error_message, parsed_count)
        """
        count_str = count_str.strip()
        
        if not count_str:
            return False, "Count cannot be empty", None
        
        try:
            count = int(count_str)
            if count < 1:
                return False, "Count must be at least 1", None
            if count > max_count:
                return False, f"Count cannot exceed {max_count} (total available accounts)", None
            return True, None, count
        except ValueError:
            return False, "Count must be a valid number", None
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """
        Sanitize user input by removing potentially dangerous characters
        
        Args:
            text: Input text
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Input truncated to {max_length} characters")
        
        return text.strip()

