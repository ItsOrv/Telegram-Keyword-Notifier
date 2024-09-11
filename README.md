# Telegram Message Monitor Bot

This project provides a Telegram bot that monitors specific groups or channels for messages containing predefined keywords. Upon detection, the bot forwards these messages to a designated Telegram channel. Additionally, it supports excluding messages from particular users.

## Key Features

- **Keyword Monitoring**: Monitors messages in specified Telegram groups or channels based on user-defined keywords.
- **Message Forwarding**: Automatically forwards detected messages to a specified Telegram channel.
- **User Exclusion**: Enables the bot to ignore messages from specific users by their Telegram user ID.
- **Logging**: Includes detailed logging for better debugging and monitoring.

## Prerequisites

- Python 3.12.1
- Telegram account
- Telegram bot token

## Installation

To install and configure the bot, run the following command in your terminal:

```bash
bash <(curl https://raw.githubusercontent.com/ItsOrv/Telegram-Message-Monitor/main/install.sh)
```

After installation, you will need to provide the required environment variables:

```bash
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
CHANNEL_ID=your_channel_id
```

### Manual Installation

To install the bot manually, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/telegram-message-monitor-bot.git
   cd telegram-message-monitor-bot
   ```

2. **Set up a virtual environment (optional but recommended)**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the environment**:
   Create a `.env` file in the project’s root directory with the following contents:
   ```bash
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   CHANNEL_ID=your_channel_id
   ```
   - `API_ID` and `API_HASH`: Obtain these from [my.telegram.org](https://my.telegram.org).
   - `BOT_TOKEN`: Generated through the BotFather on Telegram.
   - `TARGET_GROUPS`: Comma-separated list of Telegram group or channel IDs to monitor.
   - `CHANNEL_ID`: ID of the channel where messages will be forwarded.

## Usage

To run the bot, use the following command:

```bash
python3 bot.py
```

The bot will begin monitoring the specified Telegram groups or channels, forwarding any detected messages containing the specified keywords to your designated channel. Messages from ignored users will be excluded.

## Error Handling

The bot is equipped with error handling mechanisms for common scenarios, including:

- **Two-Factor Authentication (2FA)**: If 2FA is enabled, the bot will prompt for the necessary second factor.
- **General Errors**: Logs any unexpected issues that occur during message processing or while starting the client.

## Contributing

Contributions are welcome! Feel free to submit a pull request or open an issue to discuss proposed changes.

## Future Updates (TO-DO):

- **1.1**: Fix handling of private group links (prepend a 1 to the link).
- **1.2**: Support for links from Glass Telegram groups.
- **2.1**: Refactor Docker setup to support running both Python scripts simultaneously.
- **2.2**: Add CLI control for restarting/updating the bot, or possibly implement these controls via the Telegram bot interface.
- **3.1**: Create `install.sh` script (completed):
   ```bash
   bash <(curl https://raw.githubusercontent.com/ItsOrv/Telegram-Message-Monitor/main/install.sh)
   ```
- **4.1**: Combine `management.py` and `bot.py` into a single Python script.

--- 

This version is clearer, with a more professional tone and improved structure. It also provides more precise guidance and reduces redundancy. Let me know if you want to refine it further!
