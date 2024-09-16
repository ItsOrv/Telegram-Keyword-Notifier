# Telegram Message Monitor Bot

This project is a Telegram bot designed to monitor specified Telegram groups or channels for messages containing specific keywords. When such messages are detected, the bot forwards them to a designated Telegram channel. Additionally, the bot allows for the exclusion of messages from specific users.

## Features

- **Keyword Monitoring**: Automatically monitors specified Telegram groups or channels for messages containing predefined keywords.
- **Message Forwarding**: Forwards detected messages to a specified Telegram channel.
- **User Exclusion**: Supports ignoring messages from specific users based on their Telegram numeric user ID.
- **Logging**: Comprehensive logging for easy debugging and monitoring.

## Installation

### Prerequisites

- Python 3.7 or later
- A Telegram bot token (create a bot using [BotFather](https://core.telegram.org/bots#botfather))

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/telegram-message-monitor-bot.git
   cd telegram-message-monitor-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create and configure your `.env` file**:
   Create a `.env` file in the root of the project directory and add the following variables:
   ```plaintext
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   TARGET_GROUPS=group_id1,group_id2
   KEYWORDS=keyword1,keyword2
   CHANNEL_ID=@your_channel_id
   SESSION_NAME=your_session_name
   IGNORE_USERS=user_id1,user_id2
   ```
   - `API_ID` and `API_HASH`: Get these from [my.telegram.org](https://my.telegram.org).
   - `BOT_TOKEN`: The token for your bot, obtained from BotFather.
   - `TARGET_GROUPS`: A comma-separated list of group/channel IDs to monitor.
   - `KEYWORDS`: A comma-separated list of keywords to monitor.
   - `CHANNEL_ID`: The ID of the channel where you want to forward detected messages.
   - `SESSION_NAME`: A name for the session (used for session storage).
   - `IGNORE_USERS`: A comma-separated list of numeric user IDs to ignore.

## Usage

To start the bot, simply run:

```bash
python bot.py
```

The bot will begin monitoring the specified Telegram groups or channels and will forward any messages containing the specified keywords to the designated channel, excluding messages from users listed in `IGNORE_USERS`.

## Error Handling

The bot includes error handling for common issues such as:

- **Session Password Needed**: Handles 2FA-enabled accounts by logging the need for the second factor.
- **General Errors**: Logs any unexpected exceptions during message processing or client startup.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue to discuss any changes.
