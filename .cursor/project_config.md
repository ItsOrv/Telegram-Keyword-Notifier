# Project Configuration - Telegram Management Bot Panel

## Project Goals

**Primary Objective**: A comprehensive Telegram bot management system for monitoring messages, managing multiple accounts, and performing bulk operations across Telegram groups and channels.

**Key Features**:
- Multi-account Telegram session management
- Message monitoring and keyword-based forwarding
- Bulk operations (reactions, polls, joins, blocks, messages, comments)
- Individual account operations
- Statistics and reporting

## Tech Stack

### Core Technologies
- **Language**: Python 3.8+
- **Framework**: Telethon 1.36.0
- **Async Runtime**: asyncio
- **Configuration**: python-dotenv, JSON-based config
- **Logging**: Python logging module

### Dependencies
- `telethon==1.36.0` - Telegram API client
- `python-dotenv==1.0.0` - Environment variable management
- `aiohttp` - Async HTTP client
- `pysocks` - SOCKS proxy support
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage reporting

### Architecture
- **Entry Point**: `main.py`
- **Core Module**: `src/Telbot.py` (TelegramBot class)
- **Configuration**: `src/Config.py` (ConfigManager)
- **Session Management**: `src/Client.py` (SessionManager, AccountHandler)
- **Event Handlers**: `src/Handlers.py` (CommandHandler, MessageHandler, CallbackHandler)
- **Operations**: `src/actions.py` (Bulk and individual operations)
- **Monitoring**: `src/Monitor.py` (Message monitoring and forwarding)
- **UI Components**: `src/Keyboards.py` (Inline keyboards)
- **Validation**: `src/Validation.py` (Input validation)

## Coding Standards

### Code Style
- Follow PEP 8 Python style guide
- Use type hints for function parameters and return values
- Import types from `typing` module: `Dict, Any, Optional, Union`
- Use descriptive variable and function names

### Async/Await Patterns
- **ALWAYS** use `async/await` for all Telegram API calls and I/O operations
- Use `asyncio.gather()` with `return_exceptions=True` for concurrent tasks
- Use `asyncio.Semaphore` to limit concurrent operations
- Pattern in `src/actions.py`: `operation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)`

### Thread Safety
- **CRITICAL**: Always use locks when modifying `active_clients` dictionary
- Pattern:
  ```python
  async with self.tbot.active_clients_lock:
      snapshot = list(self.tbot.active_clients.items())
  ```
- Take snapshots while holding locks, release before processing to avoid deadlocks

### Error Handling
- Wrap all async operations in try-except blocks
- Log errors with appropriate levels:
  - `logger.info()` - Normal operations
  - `logger.warning()` - Recoverable issues (e.g., FloodWaitError)
  - `logger.error()` - Errors requiring attention
  - `logger.critical()` - Critical failures
- Always notify users when operations fail
- Use `exc_info=True` for exception details in logs
- Handle `FloodWaitError` with automatic retry and wait
- Handle `SessionPasswordNeededError` for 2FA

### Rate Limiting
- Use `RATE_LIMIT_SLEEP` from config for delays between operations
- Process items in batches using `GROUPS_BATCH_SIZE`
- Always respect Telegram's rate limits
- Implement exponential backoff for retries

### Configuration Management
- Use `ConfigManager` from `src/Config.py` for all configuration operations
- Always save config after modifications: `self.tbot.config_manager.save_config(self.tbot.config)`
- Access config via `self.tbot.config` dictionary
- Validate required environment variables on startup

### Logging
- Import logger at module level: `logger = logging.getLogger(__name__)`
- Log important state changes and operations
- Include context in log messages (session names, user IDs, phone numbers masked)
- Never log sensitive data (passwords, API keys, full phone numbers)

### File Path Security
- Sanitize file paths to prevent path traversal attacks
- Pattern:
  ```python
  import re
  filename = re.sub(r'[^\w\-_\.]', '', os.path.basename(filename))
  ```

## Constraints

### Security Requirements
- **NEVER** commit `.env` file to version control
- **NEVER** commit `.session` files (Telegram authentication data)
- **NEVER** log sensitive data (passwords, API keys, full phone numbers)
- Always validate and sanitize user input
- Use `InputValidator` from `src/Validation.py` for all inputs
- Always verify `ADMIN_ID` before processing sensitive operations

### Dependencies
- **NO** external dependencies without approval
- Use only dependencies listed in `requirements.txt`
- Pin dependency versions for stability
- Test compatibility before adding new dependencies

### Code Quality
- All functions must have docstrings
- All async functions must handle exceptions
- All file I/O operations must be wrapped in try-except
- All Telegram API calls must handle `FloodWaitError`
- All configuration operations must validate data

### Testing Requirements
- Run tests before merging: `pytest tests/`
- Maintain test coverage for critical paths
- Test all user flows (account management, bulk operations, monitoring)
- Test error handling and edge cases
- All tests must pass before auto-merge

### Performance
- Use semaphores to limit concurrent operations
- Process items in batches to avoid memory issues
- Clean up resources in finally blocks
- Use async locks instead of sync locks for async code

## Project Structure

```
Telegram-Panel/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (gitignored)
├── clients.json           # Client configuration (auto-generated)
├── logs/                  # Log files directory
│   └── bot.log           # Application logs
├── .cursor/              # Cursor AI configuration
│   ├── project_config.md # This file
│   ├── workflow_state.md # Dynamic workflow state
│   └── rules/           # Additional rules
└── src/                 # Source code
    ├── Telbot.py        # Main bot class
    ├── Config.py        # Configuration management
    ├── Client.py        # Session/account management
    ├── Handlers.py      # Event handlers
    ├── Keyboards.py     # Keyboard layouts
    ├── Monitor.py       # Message monitoring
    ├── actions.py       # Bulk/individual operations
    ├── Logger.py        # Logging setup
    └── Validation.py    # Input validation
```

## Model Requirements

**CRITICAL**: This project MUST use Claude Sonnet 4.5 (claude-sonnet-4-20250514) from Anthropic.
- Auto routing MUST route to Claude Sonnet 4.5
- This is a security and compliance requirement
- Do NOT use any other models (GPT-4, Gemini, etc.)

## Environment Variables

Required variables (must be in `.env`):
- `API_ID` - Telegram API ID from my.telegram.org
- `API_HASH` - Telegram API Hash from my.telegram.org
- `BOT_TOKEN` - Bot token from @BotFather
- `ADMIN_ID` - Admin user ID (must be verified before operations)
- `CHANNEL_ID` - Channel for forwarded messages

Optional variables:
- `BOT_SESSION_NAME` - Bot session file name (default: `bot_session`)
- `CLIENTS_JSON_PATH` - Client configuration file (default: `clients.json`)
- `RATE_LIMIT_SLEEP` - Sleep time to avoid rate limits (default: `60`)
- `GROUPS_BATCH_SIZE` - Groups to process per batch (default: `10`)
- `GROUPS_UPDATE_SLEEP` - Sleep time between group updates (default: `60`)

## Git Workflow

- Use feature branches for new features
- Commit changes with descriptive messages
- Run tests before committing
- Never commit `.env`, `.session`, or sensitive files
- Use meaningful commit messages

## Documentation

- Update README.md when adding features
- Document all public functions with docstrings
- Keep this file updated when standards change
- Document workflow state changes in `workflow_state.md`

