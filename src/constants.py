"""
Constants used throughout the application.
Centralizes magic numbers and configuration values.
"""
from __future__ import annotations

# Concurrency and rate limiting constants
MAX_CONCURRENT_OPERATIONS = 3
MAX_RETRY_ATTEMPTS = 3
DEFAULT_DELAY_MIN = 2.0
DEFAULT_DELAY_MAX = 5.0

# Message length limits
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
MONITOR_MESSAGE_MAX_LENGTH = 4000  # Slightly less than Telegram limit for safety

# Session name limits
MAX_SESSION_NAME_LENGTH = 255

# Poll option limits
MIN_POLL_OPTION = 1
MAX_POLL_OPTION = 10

# Report check bot delay
REPORT_CHECK_DELAY = 2  # seconds to wait for bot response

# Handler keys for conversation state management
class HandlerKeys:
    """Constants for handler dictionary keys to avoid magic strings"""
    # Reaction handler keys
    REACTION_LINK = 'reaction_link'
    REACTION_ACCOUNT = 'reaction_account'
    REACTION_NUM_ACCOUNTS = 'reaction_num_accounts'
    REACTION_IS_BULK = 'reaction_is_bulk'
    REACTION = 'reaction'
    
    # Poll handler keys
    POLL_LINK = 'poll_link'
    POLL_ACCOUNT = 'poll_account'
    POLL_NUM_ACCOUNTS = 'poll_num_accounts'
    POLL_IS_BULK = 'poll_is_bulk'
    
    # Join handler keys
    JOIN_ACCOUNT = 'join_account'
    JOIN_NUM_ACCOUNTS = 'join_num_accounts'
    
    # Leave handler keys
    LEFT_ACCOUNT = 'left_account'
    LEAVE_NUM_ACCOUNTS = 'leave_num_accounts'
    
    # Block handler keys
    BLOCK_ACCOUNT = 'block_account'
    BLOCK_NUM_ACCOUNTS = 'block_num_accounts'
    
    # Send PV handler keys
    SEND_PV_ACCOUNT = 'send_pv_account'
    SEND_PV_USER = 'send_pv_user'
    SEND_PV_NUM_ACCOUNTS = 'send_pv_num_accounts'
    
    # Comment handler keys
    COMMENT_LINK = 'comment_link'
    COMMENT_ACCOUNT = 'comment_account'
    COMMENT_NUM_ACCOUNTS = 'comment_num_accounts'
    COMMENT_IS_BULK = 'comment_is_bulk'

# Conversation state names
class ConversationStates:
    """Constants for conversation state names"""
    REACTION_LINK_HANDLER = 'reaction_link_handler'
    POLL_LINK_HANDLER = 'poll_link_handler'
    POLL_OPTION_HANDLER = 'poll_option_handler'
    JOIN_LINK_HANDLER = 'join_link_handler'
    LEFT_LINK_HANDLER = 'left_link_handler'
    BLOCK_USER_HANDLER = 'block_user_handler'
    SEND_PV_USER_HANDLER = 'send_pv_user_handler'
    SEND_PV_MESSAGE_HANDLER = 'send_pv_message_handler'
    COMMENT_LINK_HANDLER = 'comment_link_handler'
    COMMENT_TEXT_HANDLER = 'comment_text_handler'
    BULK_JOIN_LINK_HANDLER = 'bulk_join_link_handler'
    BULK_LEAVE_LINK_HANDLER = 'bulk_leave_link_handler'
    BULK_BLOCK_USER_HANDLER = 'bulk_block_user_handler'
    BULK_SEND_PV_USER_HANDLER = 'bulk_send_pv_user_handler'
    BULK_SEND_PV_MESSAGE_HANDLER = 'bulk_send_pv_message_handler'
    BULK_SEND_PV_ACCOUNT_COUNT_HANDLER = 'bulk_send_pv_account_count_handler'

# Error message constants
ERROR_MESSAGES = {
    'code': {
        'phone_code_invalid': "Invalid verification code.\n\nPlease start over with /start and try again.",
        'code_invalid': "Invalid verification code.\n\nPlease start over with /start and try again.",
        'phone_code_expired': "Verification code has expired.\n\nPlease start over with /start and enter the code faster.",
        'code_expired': "Verification code has expired.\n\nPlease start over with /start and enter the code faster.",
        'timeout': "Connection timeout.\n\nPlease check your internet and try again.",
        'default': "Error verifying code. Please start over with /start."
    },
    'password': {
        'password': "Invalid password.\n\nPlease start over with /start and try again with the correct password.",
        'timeout': "Connection timeout.\n\nPlease check your internet and try again.",
        'default': "Error verifying password. Please start over with /start."
    },
    'phone': {
        'flood': "Too many requests. Please wait a few minutes and try again.",
        'phone': "Invalid phone number. Please check the format and try again.",
        'network': "Network error. Please check your connection and try again.",
        'connection': "Network error. Please check your connection and try again.",
        'api': "API credentials error. Please contact the administrator.",
        'default': "Failed to add account. Please try again."
    },
    'general': {
        'default': "An error occurred. Please try again."
    }
}

