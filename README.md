# Telegram Panel

Enterprise-grade Telegram bot management system for monitoring messages, managing multiple accounts, and performing bulk operations.

## Overview

Telegram Panel is a comprehensive management system that enables centralized control of multiple Telegram accounts through a single bot interface. It provides capabilities for account management, message monitoring, bulk operations, and individual account actions.

## Features

### Account Management
- Multi-account support with dynamic enable/disable
- Session persistence and automatic recovery
- Account status monitoring and reporting
- Automatic detection of revoked sessions

### Message Monitoring
- Keyword-based message filtering
- Automatic forwarding to designated channels
- User ignore list management
- Real-time monitoring across all active accounts

### Bulk Operations
- Reactions: Apply reactions to messages across multiple accounts
- Polls: Vote in polls using multiple accounts
- Join/Leave: Manage group memberships in bulk
- Block: Block users across multiple accounts
- Private Messages: Send messages to users from multiple accounts
- Comments: Post comments on messages using multiple accounts

### Individual Operations
- Account-specific actions for targeted operations
- Per-account control and monitoring

### Statistics and Reporting
- Bot statistics and status overview
- Groups per account listing
- Keyword configuration overview
- Account health monitoring

## Requirements

- Python 3.8 or higher
- Telegram API credentials from [my.telegram.org](https://my.telegram.org/apps)
- Bot token from [@BotFather](https://t.me/BotFather)
- Telegram user account for admin access

## Installation

### Prerequisites

Ensure Python 3.8+ is installed:

```bash
python3 --version
```

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd Telegram-Panel
```

2. Create and activate virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment:

```bash
cp env.example .env
```

Edit `.env` with your credentials:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_user_id
CHANNEL_ID=@your_channel
```

5. Run the bot:

```bash
python main.py
```

## Configuration

### Environment Variables

Required variables:

- `API_ID`: Telegram API ID from my.telegram.org
- `API_HASH`: Telegram API Hash from my.telegram.org
- `BOT_TOKEN`: Bot token from @BotFather
- `ADMIN_ID`: Your Telegram user ID (get from @userinfobot)

Optional variables:

- `CHANNEL_ID`: Channel ID or username for message forwarding
- `BOT_SESSION_NAME`: Bot session filename (default: bot_session)
- `CLIENTS_JSON_PATH`: Path to clients configuration file (default: clients.json)
- `RATE_LIMIT_SLEEP`: Rate limit delay in seconds (default: 60)
- `GROUPS_BATCH_SIZE`: Batch size for group operations (default: 10)
- `GROUPS_UPDATE_SLEEP`: Group update interval in seconds (default: 60)
- `REPORT_CHECK_BOT`: Bot username or ID for report status checking

### Configuration File

The `config.json` file stores:

- `TARGET_GROUPS`: List of target groups for monitoring
- `KEYWORDS`: List of keywords for message filtering
- `IGNORE_USERS`: List of user IDs to ignore
- `clients`: Dictionary of client configurations

## Usage

### Starting the Bot

1. Start the bot with `/start` command in Telegram
2. Navigate through the interactive menu system

### Main Menu Options

- **Account Management**: Add, list, and manage Telegram accounts
- **Individual**: Perform operations on a single account
- **Bulk**: Execute operations across multiple accounts
- **Monitor Mode**: Configure keyword monitoring and forwarding
- **Report Status**: View statistics and account status

### Account Management

1. Select "Account Management" from main menu
2. Choose "Add Account" to add a new Telegram account
3. Enter phone number when prompted
4. Enter verification code received via Telegram
5. Enter 2FA password if enabled
6. Account will be saved and activated automatically

### Bulk Operations

1. Select "Bulk" from main menu
2. Choose operation type (reaction, poll, join, etc.)
3. Select number of accounts to use
4. Follow prompts to complete operation

### Monitor Mode

1. Select "Monitor Mode" from main menu
2. Add keywords to monitor
3. Configure target groups
4. Set up ignore list if needed
5. Messages containing keywords will be forwarded to configured channel

## Project Structure

```
Telegram-Panel/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── env.example            # Environment variables template
├── config.json            # Runtime configuration
├── clients.json           # Client session data
├── src/                   # Source code
│   ├── Config.py         # Configuration management
│   ├── Telbot.py         # Main bot orchestrator
│   ├── Client.py         # Session and account management
│   ├── Handlers.py       # Event handlers
│   ├── Keyboards.py      # UI keyboard layouts
│   ├── Monitor.py        # Message monitoring
│   ├── actions.py        # Bulk and individual operations
│   ├── Validation.py     # Input validation
│   ├── Logger.py         # Logging configuration
│   └── utils.py          # Utility functions
├── tests/                 # Test suite
├── docs/                  # Documentation
└── logs/                  # Log files
```

## Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage report:

```bash
pytest tests/ --cov=src --cov-report=html
```

## Security Considerations

- Never commit `.env` or `.session` files to version control
- Use strong 2FA passwords for Telegram accounts
- Keep session files secure and backed up
- Regularly update dependencies for security patches
- Limit access to admin user ID only
- Use secure channels for credential transmission

## Error Handling

The system includes comprehensive error handling:

- Automatic retry for transient errors
- Flood wait detection and handling
- Session revocation detection and cleanup
- Rate limiting to prevent API abuse
- Graceful degradation on failures

## Logging

Logs are written to `logs/bot.log` with the following levels:

- `INFO`: General operational information
- `WARNING`: Non-critical issues
- `ERROR`: Error conditions
- `CRITICAL`: Critical failures

## Troubleshooting

### Bot Not Starting

- Verify all required environment variables are set
- Check that `.env` file exists and is properly formatted
- Ensure bot token is valid and bot is started via @BotFather

### Account Authentication Fails

- Verify phone number format is correct
- Check that verification code is entered promptly
- Ensure 2FA password is correct if enabled

### Session Revoked Errors

- Sessions are automatically detected and removed
- Re-add account through Account Management menu
- Check for Telegram security notifications

### Rate Limiting

- System automatically handles FloodWait errors
- Operations include delays to prevent rate limiting
- Reduce concurrent operations if issues persist

## Development

### Code Structure

- Modular design with separation of concerns
- Async/await for concurrent operations
- Comprehensive error handling
- Type hints for better code clarity

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

See [LICENSE](LICENSE) file for details.

## Documentation

Additional documentation available in the `docs/` directory:

- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Documentation Index](docs/README.md)

## Support

For issues and questions:

1. Check existing documentation
2. Review error logs in `logs/bot.log`
3. Consult test suite for usage examples
4. Open an issue on the repository
