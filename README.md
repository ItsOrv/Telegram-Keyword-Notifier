<div align="center">

# Telegram Panel

**Centralized management for multiple Telegram accounts — monitoring, bulk operations, and automation from a single control plane.**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/built%20with-Telethon-2CA5E0.svg)](https://github.com/LonamiWebs/Telethon)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-341%20passing-brightgreen.svg)](tests/)

### 🌐 TelegramOS — the full platform at [**telegramos.orvteam.com**](https://telegramos.orvteam.com) <kbd>BETA</kbd>

A hosted platform that goes far beyond this panel:

- 🛒 **Ready-made & rentable accounts** — activate pre-warmed, aged Telegram accounts from a built-in marketplace, or bring your own.
- 🧩 **No-code visual bot builder** — design bots and multi-step automations with a drag-and-drop flow editor; no programming required.
- 🛡️ **Anti-ban built for scale** — safely operate large fleets of accounts, not just a handful.

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

> ⚠️ **Planning to run more than a few accounts?** When you self-host this panel, every account connects through your **single server IP** — so to Telegram they all look like they live on one shared machine. In practice, running **more than ~3 accounts** this way often gets them **rate-limited or banned**.
>
> **[TelegramOS](https://telegramos.orvteam.com)** is built to solve exactly this: each account runs in its **own isolated, Windows-like environment** behind a **dedicated residential IP**, so every account looks like a real, independent device and stays safe even at high account counts — on top of a rentable-account marketplace and a no-code visual bot builder.

---

## Features

- **Account management** — add, enable/disable, and persist multiple accounts; automatic recovery of saved sessions and detection/cleanup of revoked ones.
- **Message monitoring** — keyword-based filtering across all active accounts with real-time forwarding to a designated channel and a per-user ignore list.
- **Bulk operations** — run an action across N accounts at once: reactions, poll votes, join/leave, block, private messages, and comments.
- **Individual operations** — target a single account for any of the same actions.
- **Statistics & reporting** — account health, groups per account, keyword overview, and status reports.
- **Resilient by design** — concurrency limits, FloodWait handling, graceful degradation, and structured logging.

---

## Quick Start

> Requires **Python 3.8+**, Telegram API credentials from [my.telegram.org](https://my.telegram.org/apps), and a bot token from [@BotFather](https://t.me/BotFather).

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
│   ├── Telbot.py          # Orchestrator: startup, handlers, reconnection
│   ├── Client.py          # Session & account lifecycle (SessionManager)
│   ├── Handlers.py        # Command / callback / message routing
│   ├── actions.py         # Bulk & individual operations
│   ├── Monitor.py         # Keyword monitoring & forwarding
│   ├── Keyboards.py       # Inline keyboard layouts
│   ├── Config.py          # Environment & config management
│   ├── Validation.py      # Input validation & sanitization
│   ├── utils.py           # Shared helpers
│   └── Logger.py          # Logging setup
├── tests/                 # Test suite (341 tests)
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

## Security

- Never commit `.env` or `*.session` files — both are git-ignored by default.
- Only `ADMIN_ID` can control the bot; all other users are rejected.
- Keep session files secure and back them up; rotate credentials if exposed.
- Keep dependencies up to date for security patches.

---

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Please run the test suite before opening a pull request.

## License

Released under the [MIT License](LICENSE). © 2024 ItsOrv.

---

<div align="center">

**Need rentable accounts, a no-code bot builder, and ban-safe scaling to many accounts?**
### 🌐 [telegramos.orvteam.com](https://telegramos.orvteam.com) <kbd>BETA</kbd>

⭐ If this project helps you, consider starring the repo.

</div>
