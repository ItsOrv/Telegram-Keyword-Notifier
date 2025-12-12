#!/usr/bin/env python3
"""
Test script for config message detection
"""

def is_config_message(message):
    """
    Check if a message looks like a configuration/command message rather than actual content.
    """
    if not message:
        return True

    # Check if it's just a number (account count)
    if message.isdigit():
        return True

    # Check if it's just usernames (contains @)
    words = message.split()
    username_count = 0
    for word in words:
        if word.startswith('@'):
            username_count += 1
        elif not word.replace(' ', '').isalnum():
            # If it contains non-alphanumeric characters (except spaces), it's probably content
            break
    else:
        # If all words are either usernames or simple alphanumeric, check if it's mostly usernames
        if username_count > 0 and username_count >= len(words) * 0.7:  # 70% or more are usernames
            return len(words) <= 10  # Reasonable limit for username list

    # Check for very short messages that might be commands
    if len(message) < 3:
        return True

    # Check for messages that look like bot commands
    if message.startswith('/') or message.startswith('!') or message.startswith('.'):
        return True

    # If message is longer than 15 characters and contains normal text, it's definitely content
    if len(message) > 15 and any(char.isalpha() for char in message):
        return False

    # Messages between 3-15 characters are ambiguous, check for meaningful content
    if 3 <= len(message) <= 15:
        # If it has punctuation or multiple words, it's probably content
        if any(char in message for char in '.,!?;:') or ' ' in message:
            return False
        # Single words that are not obvious commands
        if len(message.split()) == 1 and not message.isupper():
            return False

    return False

# Test cases
test_messages = [
    '2',  # account count - should be config
    '@username',  # single username - should be config
    '@user1 @user2 @user3',  # multiple usernames - should be config
    'Hello world this is my message',  # actual message - should NOT be config
    'Hi!',  # short message with punctuation - should be content
    'Hi',  # short message - should be config
    'OK',  # short message - should be config
    '/start',  # command - should be config
    'Hello there!',  # message with punctuation - should be content
    'This is a real message that users should receive',  # real message
    'Buy now!',  # imperative with punctuation - should be content
]

print('Testing message classification:')
print('=' * 60)
for msg in test_messages:
    is_config = is_config_message(msg)
    status = 'CONFIG (ignored)' if is_config else 'CONTENT (sent)'
    print(f'"{msg}" -> {status}')

print('=' * 60)
print('Summary: Only CONTENT messages will be sent to users.')
print('CONFIG messages will be rejected with an error.')
