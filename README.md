<div align="center">

# Telegram Panel

**Centralized management for multiple Telegram accounts: monitoring, bulk operations, and automation from a single control plane.**

[![Tests](https://github.com/ItsOrv/Telegram-Panel/actions/workflows/python-app.yml/badge.svg)](https://github.com/ItsOrv/Telegram-Panel/actions/workflows/python-app.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/built%20with-Telethon-2CA5E0.svg)](https://github.com/LonamiWebs/Telethon)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

### 🌐 Also available hosted: [**telegramos.orvteam.com**](https://telegramos.orvteam.com) <kbd>BETA</kbd>

This panel is free and self-hosted, and that is the right choice for personal use
and a small number of accounts. If your use is commercial or the account count
grows, the hosted version takes the operational side off your hands:

- 🛒 **Account marketplace:** start from accounts provided on the platform, or bring your own.
- 🧩 **No-code visual bot builder:** design bots and multi-step automations with a drag-and-drop flow editor.
- 🏗️ **Managed infrastructure:** each account runs in its own isolated environment with its own network egress, instead of sharing one server.

**[→ Open TelegramOS](https://telegramos.orvteam.com)**

</div>

---

## Overview

Telegram Panel is a self-hostable system for operating many Telegram accounts from one place. It exposes the **same feature set through three interfaces**, so you can pick whatever fits your workflow:

| Interface | Best for | Entry point |
|-----------|----------|-------------|
| 🤖 **Telegram Bot** | Access from any device, on the go | `python main.py` |
| 🖥️ **Interactive CLI** | A menu-driven terminal UI on your server | `python interactive_cli.py` |
| ⚡ **Command CLI** | Scripting & automation | `python cli_main.py …` |

> **How this behaves as the account count grows.** Self-hosted, every account
> connects from the same server IP and reports the same device signature, so
> Telegram treats them as one machine. For personal use and a few accounts this
> is fine. Past that, expect rate limiting.
>
> That is a property of self-hosting, not a defect of this panel — the same
> applies to any single-server setup. If you need to run at a larger scale,
> [TelegramOS](https://telegramos.orvteam.com) gives each account its own
> isolated environment and network egress. Whichever you use, stay within
> [Telegram's Terms of Service](https://telegram.org/tos) (see
> [Acceptable use](#acceptable-use)).

---

## Features

- **Account management:** add, enable/disable, and persist multiple accounts, with automatic recovery of saved sessions and detection/cleanup of revoked ones.
- **Message monitoring:** keyword-based filtering across all active accounts, with real-time forwarding to a designated channel and a per-user ignore list.
- **Bulk operations:** run an action across N accounts at once (reactions, poll votes, join/leave, block, private messages, and comments).
- **Individual operations:** target a single account for any of the same actions.
- **Statistics & reporting:** account health, groups per account, keyword overview, and status reports.
- **Resilient by design:** concurrency limits, FloodWait handling, graceful degradation, and structured logging.

---

## Quick Start

> Requires **Python 3.11+**, Telegram API credentials from [my.telegram.org](https://my.telegram.org/apps), and a bot token from [@BotFather](https://t.me/BotFather).

```bash
# 1. Clone
git clone https://github.com/ItsOrv/Telegram-Panel.git
cd Telegram-Panel

# 2. Create an isolated environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp env.example .env               # then edit .env (see below)

# 5. Run (choose one)
python main.py                    # Telegram bot
python interactive_cli.py         # Interactive terminal UI
python cli_main.py --help         # Command-line interface
```

Minimal `.env`:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_user_id
CHANNEL_ID=@your_channel          # optional, for message forwarding
```

---

## Configuration

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `API_ID` | ✅ | — | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | — | Telegram API Hash from my.telegram.org |
| `BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `ADMIN_ID` | ✅ | — | Your Telegram user ID (only this user may control the bot) |
| `CHANNEL_ID` | ➖ | — | Channel ID/username for forwarded messages |
| `BOT_SESSION_NAME` | ➖ | `bot_session` | Bot session filename |
| `CLIENTS_JSON_PATH` | ➖ | `clients.json` | Path to the accounts/config file |
| `RATE_LIMIT_SLEEP` | ➖ | `60` | Rate-limit delay (seconds) |
| `GROUPS_BATCH_SIZE` | ➖ | `10` | Batch size for group scans |
| `GROUPS_UPDATE_SLEEP` | ➖ | `60` | Group update interval (seconds) |
| `REPORT_CHECK_BOT` | ➖ | — | Bot username/ID used for report-status checks |

Runtime state lives in **`clients.json`**: `TARGET_GROUPS`, `KEYWORDS`, `IGNORE_USERS`, `clients`, and `inactive_accounts`.

---

## Usage

### Telegram bot

```bash
python main.py
```

Send `/start` to your bot (only `ADMIN_ID` is authorized) and navigate the inline menu: **Account Management**, **Individual**, **Bulk**, **Monitor Mode**, and **Report Status**.

### Command-line examples

```bash
# List configured accounts
python cli_main.py list-accounts

# Add an account (interactive login)
python cli_main.py add-account +1234567890

# React with 5 accounts to a message
python cli_main.py bulk reaction 5 "https://t.me/c/123456/789" 👍

# Vote in a poll with a single account
python cli_main.py individual vote my_session "https://t.me/channel/42" 2
```

Full command reference: [docs/CLI.md](docs/CLI.md) · Interactive guide: [docs/INTERACTIVE_CLI.md](docs/INTERACTIVE_CLI.md)

---

## Architecture

```
Telegram-Panel/
├── main.py                # Bot entry point
├── cli_main.py            # Command-line entry point
├── interactive_cli.py     # Interactive TUI entry point
├── src/
│   ├── telbot.py          # Orchestrator: startup, handlers, reconnection
│   ├── client.py          # Session & account lifecycle (SessionManager)
│   ├── handlers.py        # Command / callback / message routing
│   ├── actions.py         # Bulk & individual operations
│   ├── monitor.py         # Keyword monitoring & forwarding
│   ├── keyboards.py       # Inline keyboard layouts
│   ├── config.py          # Environment & config management
│   ├── validation.py      # Input validation & sanitization
│   ├── utils.py           # Shared helpers
│   └── logger.py          # Logging setup
├── tests/                 # Test suite
└── docs/                  # Documentation
```

Built on [Telethon](https://github.com/LonamiWebs/Telethon) with an `asyncio`-first design: a single event loop per CLI invocation, a bounded concurrency semaphore for bulk work, and lock-guarded shared state.

---

## Testing

```bash
pytest tests/                                   # run the suite
pytest tests/ --cov=src --cov-report=html       # with coverage
```

---

## Acceptable use

This is an automation tool for accounts you own or are authorised to operate.

- Telegram accounts are personal and non-transferable under
  [Telegram's Terms of Service](https://telegram.org/tos). Do not use this to
  operate accounts that are not yours to operate.
- Bulk messaging, joining, and reactions are easy to turn into spam. Sending
  unsolicited messages is against Telegram's ToS and, in many countries, against
  the law.
- Anti-spam limits exist for a reason. This project does not try to defeat them,
  and issues asking for help doing so will be closed.
- You are responsible for how you use it. The MIT licence gives you no warranty.

## Security

- Never commit `.env` or `*.session` files; both are git-ignored by default.
- Only `ADMIN_ID` can control the bot; all other users are rejected.
- Keep session files secure and back them up; rotate credentials if exposed.
- Keep dependencies up to date for security patches.

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), and please run the test suite before opening a pull request.

## License

Released under the [MIT License](LICENSE). © 2024 ItsOrv.

---

<div align="center">

Running this commercially, or across more accounts than one server can carry?
### 🌐 [telegramos.orvteam.com](https://telegramos.orvteam.com) <kbd>BETA</kbd>

⭐ If this project helps you, consider starring the repo.

</div>
