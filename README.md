# Telegram Panel

Telegram Panel is a comprehensive tool designed to manage multiple Telegram accounts, monitor groups or channels, and automate messaging operations based on predefined rules. This project provides a robust bot that can monitor specific groups or channels for messages containing keywords, automatically forward them to designated channels, exclude specific users, and manage various messaging automation features. 

## Features

### Core Functionality
- **Multi-Account Management**: Manages multiple Telegram accounts, enabling batch operations on a large scale.
- **Keyword Monitoring**: Monitors specified Telegram groups or channels for user-defined keywords.
- **Message Forwarding**: Automatically forwards detected messages containing keywords to pre-configured channels based on category.
- **User Exclusion**: Ignores messages from specific users by their Telegram user ID, ensuring irrelevant messages are not forwarded.
- **Logging and Error Handling**: Provides detailed logs for easier debugging and efficient monitoring. Handles common errors, including two-factor authentication (2FA) prompts and general message processing issues.
- **Automated Post-Liking**: (soon) Synchronize all accounts within the panel to like a specific post, enabling quick engagement for promoting specific posts or advertisements.
- **Channel Joining for All Accounts**: (soon) Enroll multiple accounts into one or more Telegram channels simultaneously.
- **User Blocking**: (soon) Block specific users across all managed accounts by providing a list of user IDs.
- **Mass Advertising via Direct Messages**: (soon) Select from a list of advertising messages stored in a .txt file within the bot. The bot sends these messages to targeted users either based on user ID or by finding users within mutual groups.
- **Auto-Reply for Customer Support**: (soon) Accounts can automatically respond to incoming messages.
- **Account Activity Monitoring and Analytics**: (soon) A dashboard provides insights into each account's activity, including group memberships, messages sent, and user interactions, helping with performance and engagement tracking.

  - **Automated Direct Messages**: When a keyword is detected, the bot can send a message from one of the managed accounts to the message sender.
  - **User Detection and ID Management**: (soon)
    - If the sender’s ID is available, selects an account not already in a group with the user to send a message.
    - If the ID is unavailable, selects an account within the same group as the user to send a message.

- **Categorized Keyword Monitoring**: (soon) Allows monitoring with multiple keyword categories, each linked to a specific channel for forwarding, making it possible to track multiple topics or products simultaneously.

### Docker Integration with CLI
- **Containerized Environment**: (soon) This bot runs within a Docker container for consistency and easier deployment.
- **CLI Command Control**: (soon) With the `tmm` command, you can start, stop, restart, and update the bot easily within the Docker environment. You can also manage configurations and check for updates directly from the CLI.

## Prerequisites

- Python 3.12.1
- Telegram account(s) with Bot API token(s)
- Docker and Docker Compose (recommended for deployment)

## Installation (NOT READY, INSTALL MANUALLY)

### Automated Installation (Docker)
For Docker installation, execute the following command:

```bash
bash <(curl -s https://raw.githubusercontent.com/ItsOrv/Telegram-Panel/main/install.sh)
```

This script will:
- Install Docker and Docker Compose
- Clone the project repository
- Prompt for required environment variables
- Configure the environment and create a `.env` file
- Build and deploy the Docker container
- Add the `tmm` command for managing the bot

### Environment Variables

During the installation, you’ll need to provide the following environment variables:

```bash
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
CHANNEL_ID=your_channel_id
```

- **API_ID** and **API_HASH**: Obtain these from [my.telegram.org](https://my.telegram.org).
- **BOT_TOKEN**: Generated via BotFather on Telegram.
- **CHANNEL_ID**: ID of the target channel for forwarding messages.

### Using the `tmm` Command

The `tmm` command allows you to manage the Docker container. Options include:
1. **Start**: Starts the container if it’s not already running.
2. **Stop**: Stops the container if it’s currently running.
3. **Restart**: Restarts the container and checks for correct installation.
4. **Update**: Pulls the latest changes from GitHub and rebuilds the container.
5. **Uninstall**: Stops and removes the Docker container, project files, and `tmm` command.

### Manual Installation

To install manually without Docker, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/ItsOrv/Telegram-Panel.git
   cd Telegram-Panel
   ```

2. Set up a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the environment:
   Create a `.env` file with the following details:
   ```bash
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   CHANNEL_ID=your_channel_id
   ```

## Usage

To start the bot manually, use:
```bash
python3 src/main.py
```

The bot will monitor specified Telegram groups or channels, forwarding detected messages to designated channels, and managing automated messaging based on predefined rules.

## Future Updates

### Planned Features
- **Automated Message Sending**: A feature to send predefined messages directly to users who trigger keywords. This can be configured with specific messages stored in a text file and set to automatically send when triggered.
- **Enhanced Multi-Category Monitoring**: Support for multiple keyword categories with each category linked to a unique destination channel, simplifying multi-topic tracking.
- **Real-Time Monitoring with Prioritization**: Fine-tune keyword monitoring to prioritize urgent messages or topics.
- **Advanced Analytics and Logging**: Improved logging for detailed performance insights, error tracking, and usage analytics.

## Error Handling

The bot includes mechanisms to handle various errors:
- **Two-Factor Authentication (2FA)**: Prompts for a second factor if 2FA is enabled on any account.
- **Client Authorization**: Checks for client authorization and skips unauthorized accounts.
- **Connection Issues**: Logs and retries for connectivity issues, ensuring reliability across multiple accounts.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue if you’d like to add new features or report bugs.

---

Feel free to adjust any details as needed for your setup.
