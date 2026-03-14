# Interactive CLI Guide

The Interactive CLI is part of Method 2 (CLI usage) of Telegram Panel. It provides a menu-driven interface similar to the Telegram bot, allowing you to manage Telegram accounts and perform operations directly from your server or local system terminal.

**Note:** This is the recommended CLI method. For command-line automation, see [CLI.md](CLI.md).

## Features

- **Menu Navigation**: Navigate with arrow keys (↑↓) and select with Enter
- **Visual Interface**: Rich terminal UI with colors and formatting (when available)
- **All Features**: Access to all bot features without Telegram
- **Easy Navigation**: Back buttons and intuitive menu structure

## Installation

The interactive CLI requires additional dependencies:

```bash
pip install prompt-toolkit rich
```

These are automatically installed when you run:

```bash
pip install -r requirements.txt
```

## Usage

Start the interactive CLI:

```bash
python interactive_cli.py
```

## Navigation

### With prompt_toolkit (Recommended)

When `prompt-toolkit` is available:
- Use **arrow keys (↑↓)** to navigate menus
- Press **Enter** to select an option
- Press **Esc** to cancel/go back

### With rich (Fallback)

When only `rich` is available:
- Menu is displayed as a numbered list
- Type the **number** of the option you want
- Press **Enter** to confirm

### Simple Mode (Fallback)

When neither library is available:
- Menu is displayed as a numbered list
- Type the **number** of the option you want
- Press **Enter** to confirm

## Menu Structure

### Main Menu

- **Account Management**: Add, list, and remove accounts
- **Individual Operations**: Perform operations on a single account
- **Bulk Operations**: Execute operations across multiple accounts
- **Monitor Mode**: Configure keyword monitoring (coming soon)
- **Statistics & Report**: View account statistics
- **Exit**: Exit the application

### Account Management

- **Add Account**: Add a new Telegram account
  - Enter phone number (e.g., +1234567890)
  - Enter verification code from Telegram
  - Enter 2FA password if enabled
  
- **List Accounts**: View all available accounts
  
- **Remove Account**: Remove an account from the system
  - Select account from list
  - Confirm removal

### Individual Operations

Select an account first, then choose an operation:

- **Reaction**: Apply reaction to a message
  - Enter message link
  - Select reaction emoji
  
- **Vote in Poll**: Vote in a poll
  - Enter poll link
  - Enter option number (1-10)
  
- **Join Group/Channel**: Join a group or channel
  - Enter group/channel link
  
- **Leave Group/Channel**: Leave a group or channel
  - Enter group/channel link
  
- **Block User**: Block a user
  - Enter username or user ID
  
- **Send Private Message**: Send a message to a user
  - Enter username or user ID
  - Enter message text
  
- **Post Comment**: Post a comment on a message
  - Enter message link
  - Enter comment text

### Bulk Operations

Select number of accounts, then choose an operation:

- **Bulk Reaction**: Apply reaction with multiple accounts
- **Bulk Vote**: Vote in poll with multiple accounts
- **Bulk Join**: Join group/channel with multiple accounts
- **Bulk Leave**: Leave group/channel with multiple accounts
- **Bulk Block**: Block user with multiple accounts
- **Bulk Send PV**: Send private message with multiple accounts
- **Bulk Comment**: Post comment with multiple accounts

## Examples

### Adding an Account

1. Start interactive CLI: `python interactive_cli.py`
2. Select "Account Management"
3. Select "Add Account"
4. Enter phone number: `+1234567890`
5. Enter verification code from Telegram
6. Enter 2FA password if prompted
7. Account is added and ready to use

### Applying Bulk Reaction

1. Start interactive CLI: `python interactive_cli.py`
2. Select "Bulk Operations"
3. Select "Bulk Reaction"
4. Enter number of accounts: `5`
5. Enter message link
6. Select reaction emoji
7. Operation executes across selected accounts

### Individual Vote

1. Start interactive CLI: `python interactive_cli.py`
2. Select "Individual Operations"
3. Select "Vote in Poll"
4. Select account from list
5. Enter poll link
6. Enter option number
7. Vote is cast

## Keyboard Shortcuts

- **Ctrl+C**: Exit application (anywhere)
- **Esc**: Cancel/go back (in prompt_toolkit mode)
- **Enter**: Confirm selection
- **Arrow Keys**: Navigate menus (in prompt_toolkit mode)

## Troubleshooting

### Menu Not Showing Properly

If menus don't display correctly:
- Ensure terminal supports ANSI colors
- Try resizing terminal window
- Check if `prompt-toolkit` or `rich` is installed

### Arrow Keys Not Working

If arrow keys don't work:
- The system will fall back to number-based selection
- Type the number of the option you want
- Press Enter to confirm

### Import Errors

If you see import errors:
```bash
pip install prompt-toolkit rich
```

### Account Not Found

If account is not found:
- Ensure account was added successfully
- Check that session files exist in the project directory
- Verify account is enabled in configuration

## Differences from Telegram Bot

- **No Real-time Updates**: Operations execute immediately, no waiting for bot responses
- **Direct Input**: Enter values directly instead of through bot messages
- **Terminal-based**: All interaction happens in terminal
- **No Notifications**: No Telegram notifications for operations

## Tips

- Use arrow keys for faster navigation (when available)
- Press Ctrl+C to exit at any time
- Account sessions are shared with the bot (if both are used)
- All operations are logged to `logs/bot.log`

