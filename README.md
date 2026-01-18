# Telegram Panel

Enterprise-grade Telegram bot management system for monitoring messages, managing multiple accounts, and performing bulk operations across Telegram groups and channels.

## Overview

Telegram Panel is a comprehensive solution for managing multiple Telegram accounts through a single bot interface. It provides automated message monitoring, bulk operations, and account management with robust error handling, rate limiting, and thread-safe operations.

**Status:** This project is under active development. Refer to [INCOMPLETE_FEATURES.md](INCOMPLETE_FEATURES.md) for details on remaining work.

## Features

### Account Management
- Multi-account support with dynamic enable/disable
- Automatic session detection and management
- Account status monitoring and statistics
- Inactive account tracking
- Group synchronization across accounts

### Message Monitoring
- Keyword-based message filtering
- Automatic forwarding to designated channels
- User ignore list management
- Real-time message processing
- Source and sender tracking

### Bulk Operations
- **Reactions**: Apply reactions to messages using multiple accounts
- **Polls**: Vote on polls with multiple accounts
- **Join/Leave**: Join or leave groups/channels in bulk
- **Block**: Block users across multiple accounts
- **Private Messages**: Send private messages to users
- **Comments**: Post comments and replies to messages

### Individual Operations
- Account-specific actions
- Private message sending
- Group join/leave operations
- Comment posting
- Reaction management

### Statistics & Reporting
- Bot statistics dashboard
- Groups per account display
- Keyword configuration overview
- Ignored users list
- Account report status checking

## Prerequisites

- Python 3.8 or higher
- Telegram API credentials (API_ID and API_HASH from [my.telegram.org](https://my.telegram.org/apps))
- Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Admin user ID

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ItsOrv/Telegram-Panel.git
cd Telegram-Panel
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Alternatively, use the installation script:

```bash
chmod +x install.sh
./install.sh
```

### 3. Configure environment variables

Copy the example environment file:

```bash
cp env.example .env
```

Edit `.env` and configure your credentials:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_user_id
CHANNEL_ID=@your_channel
```

### 4. Run the bot

```bash
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `API_ID` | Telegram API ID | Yes | - |
| `API_HASH` | Telegram API Hash | Yes | - |
| `BOT_TOKEN` | Bot token from @BotFather | Yes | - |
| `ADMIN_ID` | Your Telegram user ID | Yes | - |
| `CHANNEL_ID` | Channel for forwarded messages | Yes | - |
| `BOT_SESSION_NAME` | Bot session file name | No | `bot_session` |
| `CLIENTS_JSON_PATH` | Client configuration file | No | `clients.json` |
| `RATE_LIMIT_SLEEP` | Sleep time to avoid rate limits (seconds) | No | `60` |
| `GROUPS_BATCH_SIZE` | Groups to process per batch | No | `10` |
| `GROUPS_UPDATE_SLEEP` | Sleep time between group updates | No | `60` |
| `REPORT_CHECK_BOT` | Report check bot username/ID | No | - |

### Configuration Files

- `clients.json`: Stores account and group information (auto-generated)
- `logs/bot.log`: Application logs

## Usage

### Getting Started

1. Start the bot with `/start` command
2. Navigate through the main menu:
   - Account Management
   - Individual Operations
   - Bulk Operations
   - Monitor Mode
   - Report

### Account Management

**Add Account:**
1. Navigate to Account Management → Add Account
2. Enter phone number (with country code, e.g., +1234567890)
3. Enter verification code from Telegram
4. Enter 2FA password (if enabled)

**List Accounts:**
- View all added accounts with their status
- Enable/disable accounts using toggle buttons
- Delete accounts when no longer needed

**Update Groups:**
- Scans all active accounts for groups
- Updates the database with group information
- Required before using bulk operations

### Monitor Mode

**Add Keywords:**
- Messages containing these keywords will be forwarded
- Case-insensitive matching

**Ignore Users:**
- Add user IDs to ignore their messages
- Useful for filtering spam or unwanted content

**Show Statistics:**
- Display groups count for each account
- List all configured keywords
- View all ignored user IDs

### Bulk Operations

Perform actions using multiple accounts simultaneously:

1. Select the operation (Reaction, Poll, Join, Leave, Block, Send PV, Comment)
2. Choose how many accounts to use
3. Provide required information (link, message, etc.)

**Example: Bulk Reaction**
1. Navigate to Bulk → Reaction
2. Select number of accounts
3. Provide message link
4. Select reaction emoji
5. Bot applies reaction using selected accounts

### Individual Operations

Perform actions using a specific account:

1. Select the operation
2. Choose the account to use
3. Provide required information

## Project Structure

```
Telegram-Panel/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── env.example            # Environment variables template
├── install.sh             # Installation script
├── README.md              # This file
├── INCOMPLETE_FEATURES.md # List of incomplete features
├── CHANGELOG.md           # Version history
├── CONTRIBUTING.md        # Contribution guidelines
├── LICENSE                # License file
├── docs/                  # Documentation
│   ├── README.md
│   ├── PROJECT_STRUCTURE.md
│   ├── SYSTEM_DESIGN.md
│   ├── TEST_SUMMARY.md
│   └── ...
├── logs/                  # Log files
│   └── bot.log
├── src/                   # Source code
│   ├── Config.py         # Configuration management
│   ├── Telbot.py         # Main bot class
│   ├── Client.py         # Account/session management
│   ├── Handlers.py       # Event handlers
│   ├── Keyboards.py      # Keyboard layouts
│   ├── Monitor.py        # Message monitoring
│   ├── actions.py        # Bulk/individual actions
│   ├── Validation.py     # Input validation
│   └── Logger.py         # Logging setup
└── tests/                # Test suite
    ├── test_unit_*.py    # Unit tests
    ├── test_flows_*.py   # Flow tests
    └── test_integration_*.py  # Integration tests
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/test_unit_*.py          # Unit tests
pytest tests/test_flows_*.py         # Flow tests
pytest tests/test_integration_*.py   # Integration tests
```

## Security Considerations

1. **Never share your `.env` file** - it contains sensitive credentials
2. **Keep session files secure** - they provide access to accounts
3. **Use strong 2FA passwords** for Telegram accounts
4. **Regularly update dependencies** to patch security vulnerabilities
5. **Monitor bot logs** for suspicious activities
6. **Validate all user inputs** to prevent injection attacks

## Troubleshooting

### Bot doesn't respond
- Verify bot token is correct
- Check ADMIN_ID matches your user ID
- Review logs in `logs/bot.log`

### Account authorization fails
- Ensure API_ID and API_HASH are correct
- Check phone number format (+country_code)
- Verify 2FA password if enabled

### Rate limit errors
- Increase `RATE_LIMIT_SLEEP` value
- Reduce `GROUPS_BATCH_SIZE`
- Wait before retrying operations

### Messages not forwarding
- Verify keywords are configured
- Check if users are not in ignore list
- Ensure bot has access to CHANNEL_ID
- Confirm accounts are active and authorized

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check logs in `logs/bot.log` for error details
- Refer to Telethon documentation: https://docs.telethon.dev/

## Disclaimer

This bot is for educational and legitimate purposes only. Users are responsible for complying with Telegram's Terms of Service and applicable laws. Misuse of this tool may result in account bans or legal consequences.
