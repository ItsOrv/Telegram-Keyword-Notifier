# Telegram Management Bot Panel

A comprehensive Telegram bot management system for monitoring messages, managing multiple accounts, and performing bulk operations across Telegram groups and channels.

## Features

### 🤖 Account Management
- Add multiple Telegram accounts
- Enable/disable accounts dynamically
- View account status and statistics
- Auto-detect and manage Telegram groups

### 📊 Message Monitoring
- Monitor messages based on keywords
- Forward filtered messages to a designated channel
- Ignore specific users
- Track message sources and senders

### 🔄 Bulk Operations
- **Reaction**: Apply reactions to messages using multiple accounts
- **Poll**: Vote on polls with multiple accounts
- **Join**: Join groups/channels with multiple accounts
- **Block**: Block users across multiple accounts
- **Send PV**: Send private messages to users
- **Comment**: Reply to messages/posts

### 👤 Individual Operations
- Perform actions using specific accounts
- Send private messages
- Join/leave groups
- Post comments

### 📈 Statistics & Reports
- View bot statistics
- Display groups per account
- Show configured keywords
- List ignored users

## Prerequisites

- Python 3.8 or higher
- Telegram API credentials (API_ID and API_HASH)
- A Telegram bot token
- Admin user ID

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Telegram-Panel
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or use the installation script:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Configure environment variables**
   
   Copy the example environment file:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and fill in your credentials:
   ```env
   # Get API_ID and API_HASH from https://my.telegram.org/apps
   API_ID=your_api_id
   API_HASH=your_api_hash
   
   # Get BOT_TOKEN from @BotFather
   BOT_TOKEN=your_bot_token
   
   # Your Telegram user ID (get from @userinfobot)
   ADMIN_ID=your_user_id
   
   # Channel ID or username where filtered messages will be sent
   CHANNEL_ID=@your_channel or -100xxxxxxxxxx
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `API_ID` | Telegram API ID from my.telegram.org | Yes | - |
| `API_HASH` | Telegram API Hash from my.telegram.org | Yes | - |
| `BOT_TOKEN` | Bot token from @BotFather | Yes | - |
| `ADMIN_ID` | Your Telegram user ID | Yes | - |
| `CHANNEL_ID` | Channel for forwarded messages | Yes | - |
| `BOT_SESSION_NAME` | Bot session file name | No | `bot_session` |
| `CLIENTS_JSON_PATH` | Client configuration file | No | `clients.json` |
| `RATE_LIMIT_SLEEP` | Sleep time to avoid rate limits (seconds) | No | `60` |
| `GROUPS_BATCH_SIZE` | Groups to process per batch | No | `10` |
| `GROUPS_UPDATE_SLEEP` | Sleep time between group updates | No | `60` |

### Configuration Files

- **clients.json**: Stores account and group information
- **logs/bot.log**: Contains bot operation logs

## Usage

### Getting Started

1. Start the bot with `/start` command
2. You'll see the main menu with following options:
   - 🔐 Account Management
   - 👤 Individual Operations
   - 🔄 Bulk Operations
   - 📊 Monitor Mode
   - 📈 Report

### Account Management

**Add Account:**
1. Click "Account Management" → "Add Account"
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

**Remove Keywords:**
- Remove keywords from the monitoring list

**Ignore Users:**
- Add user IDs to ignore their messages
- Useful for filtering spam or unwanted content

**Remove Ignored Users:**
- Remove users from the ignore list

**Show Groups:**
- Display groups count for each account

**Show Keywords:**
- List all configured keywords

**Show Ignores:**
- View all ignored user IDs

### Bulk Operations

Perform actions using multiple accounts simultaneously:

1. Select the operation (Reaction, Poll, Join, Block, Send PV, Comment)
2. Choose how many accounts to use
3. Provide required information (link, message, etc.)

**Example: Bulk Reaction**
1. Click "Bulk" → "Reaction"
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
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── env.example            # Environment variables template
├── install.sh             # Installation script
├── clients.json           # Client configuration (auto-generated)
├── logs/
│   └── bot.log           # Application logs
└── src/
    ├── Config.py         # Configuration management
    ├── Telbot.py         # Main bot class
    ├── Client.py         # Account/session management
    ├── Handlers.py       # Event handlers
    ├── Keyboards.py      # Keyboard layouts
    ├── Monitor.py        # Message monitoring
    ├── actions.py        # Bulk/individual actions
    └── Logger.py         # Logging setup
```

## Security Considerations

1. **Never share your `.env` file** - it contains sensitive credentials
2. **Keep session files secure** - they provide access to accounts
3. **Use strong 2FA passwords** for Telegram accounts
4. **Regularly update dependencies** to patch security vulnerabilities
5. **Monitor bot logs** for suspicious activities

## Troubleshooting

### Bot doesn't respond
- Check if bot token is correct
- Verify ADMIN_ID matches your user ID
- Review logs in `logs/bot.log`

### Account authorization fails
- Ensure API_ID and API_HASH are correct
- Check if phone number format is correct (+country_code)
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

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check logs in `logs/bot.log` for error details
- Refer to Telethon documentation: https://docs.telethon.dev/

## Disclaimer

This bot is for educational and legitimate purposes only. Users are responsible for complying with Telegram's Terms of Service and applicable laws. Misuse of this tool may result in account bans or legal consequences.

---

**Note**: This is a powerful automation tool. Use responsibly and respect Telegram's rate limits and policies.
