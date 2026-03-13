# CLI Usage Guide

Telegram Panel CLI (Command Line Interface) is the second method of using Telegram Panel. It allows you to manage Telegram accounts and perform operations directly from your server or local system, without using the Telegram bot interface.

**Note:** This is Method 2 of using Telegram Panel. Method 1 is using the Telegram Bot interface. Both methods provide the same functionality.

## Installation

Make sure you have installed all dependencies:

```bash
pip install -r requirements.txt
```

## Basic Usage

Run CLI commands using:

```bash
python cli_main.py [COMMAND] [OPTIONS]
```

Or make it executable:

```bash
chmod +x cli_main.py
./cli_main.py [COMMAND] [OPTIONS]
```

## Account Management

### List Accounts

```bash
python cli_main.py list-accounts
```

### Add Account

```bash
python cli_main.py add-account +1234567890
```

You will be prompted to:
1. Enter verification code received via Telegram
2. Enter 2FA password if enabled

### Remove Account

```bash
python cli_main.py remove-account SESSION_NAME
```

## Individual Operations

### Apply Reaction

```bash
python cli_main.py individual reaction SESSION_NAME LINK REACTION
```

Reactions: `👍`, `❤️`, `😂`, `😮`, `😢`, `😡`

Example:
```bash
python cli_main.py individual reaction +1234567890 "https://t.me/c/123456/789" 👍
```

### Vote in Poll

```bash
python cli_main.py individual vote SESSION_NAME LINK OPTION_NUMBER
```

Example:
```bash
python cli_main.py individual vote +1234567890 "https://t.me/c/123456/789" 1
```

### Join Group/Channel

```bash
python cli_main.py individual join SESSION_NAME LINK
```

Example:
```bash
python cli_main.py individual join +1234567890 "https://t.me/username"
```

### Leave Group/Channel

```bash
python cli_main.py individual leave SESSION_NAME LINK
```

### Block User

```bash
python cli_main.py individual block SESSION_NAME USERNAME_OR_ID
```

### Send Private Message

```bash
python cli_main.py individual send-pv SESSION_NAME USERNAME_OR_ID "MESSAGE_TEXT"
```

### Post Comment

```bash
python cli_main.py individual comment SESSION_NAME LINK "COMMENT_TEXT"
```

## Bulk Operations

### Bulk Reaction

```bash
python cli_main.py bulk reaction NUM_ACCOUNTS LINK REACTION
```

Example:
```bash
python cli_main.py bulk reaction 5 "https://t.me/c/123456/789" 👍
```

### Bulk Vote

```bash
python cli_main.py bulk vote NUM_ACCOUNTS LINK OPTION_NUMBER
```

### Bulk Join

```bash
python cli_main.py bulk join NUM_ACCOUNTS LINK
```

### Bulk Leave

```bash
python cli_main.py bulk leave NUM_ACCOUNTS LINK
```

### Bulk Block

```bash
python cli_main.py bulk block NUM_ACCOUNTS USERNAME_OR_ID
```

### Bulk Send Private Message

```bash
python cli_main.py bulk send-pv NUM_ACCOUNTS USERNAME_OR_ID "MESSAGE_TEXT"
```

### Bulk Comment

```bash
python cli_main.py bulk comment NUM_ACCOUNTS LINK "COMMENT_TEXT"
```

## Examples

### Complete Workflow

```bash
# List available accounts
python cli_main.py list-accounts

# Add a new account
python cli_main.py add-account +1234567890

# Apply reaction with one account
python cli_main.py individual reaction +1234567890 "https://t.me/c/123456/789" 👍

# Apply reaction with 5 accounts
python cli_main.py bulk reaction 5 "https://t.me/c/123456/789" 👍

# Join a channel with 3 accounts
python cli_main.py bulk join 3 "https://t.me/username"
```

## Notes

- All operations require valid API_ID and API_HASH in `.env` file
- Session files are stored in the project directory
- Accounts are automatically saved after adding
- CLI operations are independent of the Telegram bot

