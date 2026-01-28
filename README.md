# Telegram Panel

Enterprise-grade Telegram bot management system for monitoring messages, managing multiple accounts, and performing bulk operations.

## Features

- **Account Management**: Multi-account support with dynamic enable/disable
- **Message Monitoring**: Keyword-based filtering and automatic forwarding
- **Bulk Operations**: Reactions, polls, join/leave, block, private messages, comments
- **Individual Operations**: Account-specific actions
- **Statistics**: Bot stats, groups per account, keyword overview

## Quick Start

### Prerequisites

- Python 3.8+
- Telegram API credentials ([my.telegram.org](https://my.telegram.org/apps))
- Bot token ([@BotFather](https://t.me/BotFather))

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Telegram-Panel

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your credentials

# Run bot
python main.py
```

### Configuration

Required environment variables:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_user_id
CHANNEL_ID=@your_channel
```

## Usage

1. Start bot with `/start` command
2. Navigate through menus:
   - **Account Management**: Add/list accounts
   - **Individual**: Single account operations
   - **Bulk**: Multi-account operations
   - **Monitor Mode**: Keyword monitoring
   - **Report**: Statistics and status

## Project Structure

```
Telegram-Panel/
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── env.example         # Environment template
├── src/                # Source code
│   ├── Config.py      # Configuration
│   ├── Telbot.py      # Main bot
│   ├── Client.py      # Account management
│   ├── Handlers.py    # Event handlers
│   ├── Keyboards.py   # UI layouts
│   ├── Monitor.py     # Message monitoring
│   ├── actions.py     # Operations
│   └── Validation.py  # Input validation
└── tests/             # Test suite
```

## Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Security

- Never commit `.env` or `.session` files
- Use strong 2FA passwords
- Keep session files secure
- Regularly update dependencies

## License

See LICENSE file for details.
