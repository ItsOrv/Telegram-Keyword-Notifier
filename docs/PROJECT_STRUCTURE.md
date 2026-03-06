# Project Structure

Complete overview of project organization and file structure.

## Directory Structure

```
Telegram-Panel/
├── docs/                      # Documentation
│   ├── README.md             # Documentation index
│   ├── PROJECT_STRUCTURE.md  # This file
│   └── API.md               # API reference
├── src/                      # Source code
│   ├── __init__.py
│   ├── Config.py            # Configuration management
│   ├── Telbot.py            # Main bot orchestrator
│   ├── Client.py            # Session and account management
│   ├── Handlers.py          # Event handlers
│   ├── Keyboards.py         # UI keyboard layouts
│   ├── Monitor.py           # Message monitoring
│   ├── actions.py           # Bulk and individual operations
│   ├── Validation.py        # Input validation
│   ├── Logger.py            # Logging configuration
│   └── utils.py             # Utility functions
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   ├── run_tests.py         # Test runner
│   ├── test_account_persistence.py
│   ├── test_admin.py
│   ├── test_all_buttons.py
│   ├── test_bulk_send_pv_flow.py
│   ├── test_config_detection.py
│   ├── test_flows_account_management.py
│   ├── test_flows_bulk_operations.py
│   ├── test_flows_individual_operations.py
│   ├── test_flows_monitor_mode.py
│   ├── test_handler_flows.py
│   ├── test_handlers.py
│   ├── test_integration_edge_cases.py
│   ├── test_memory_session.py
│   ├── test_network.py
│   ├── test_session_isolation.py
│   ├── test_unit_config.py
│   ├── test_unit_handlers.py
│   ├── test_unit_keyboards.py
│   └── test_unit_validation.py
├── logs/                     # Log files
│   └── bot.log              # Application logs
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── env.example              # Environment variables template
├── config.json              # Runtime configuration
├── clients.json             # Client session data
├── install.sh               # Installation script
├── README.md                # Main project documentation
├── CONTRIBUTING.md          # Contribution guidelines
├── CHANGELOG.md             # Version history
└── LICENSE                  # License file
```

## Core Components

### Main Entry Point

**main.py**
- Application entry point
- Initializes logging
- Creates and runs TelegramBot instance
- Handles graceful shutdown

### Source Modules

#### Config.py
Configuration management system.

**Classes:**
- `ConfigManager`: Manages JSON configuration files

**Functions:**
- `validate_env_file()`: Validates required environment variables
- `get_env_variable()`: Retrieves environment variables
- `get_env_int()`: Retrieves integer environment variables

**Configuration Variables:**
- `API_ID`, `API_HASH`: Telegram API credentials
- `BOT_TOKEN`: Bot authentication token
- `ADMIN_ID`: Admin user ID
- `CHANNEL_ID`: Target channel for forwarding
- Rate limiting and batch size configurations

#### Telbot.py
Main bot orchestrator managing all system components.

**Classes:**
- `TelegramBot`: Main bot class

**Key Responsibilities:**
- Bot connection and lifecycle management
- Component initialization
- Handler registration
- Client management coordination
- Admin notifications

#### Client.py
Session and account management.

**Classes:**
- `SessionManager`: Manages Telegram client sessions
- `AccountHandler`: Handles account-related operations

**Key Features:**
- Session detection and loading
- Account authentication
- Session persistence
- Account status checking
- Group management
- Report status checking

#### Handlers.py
Event handlers for bot interactions.

**Classes:**
- `CommandHandler`: Handles bot commands
- `CallbackHandler`: Handles callback queries
- `MessageHandler`: Handles text messages
- `AccountHandler`: Account management handlers
- `KeywordHandler`: Keyword management handlers
- `StatsHandler`: Statistics and reporting handlers

**Key Features:**
- Command processing (`/start`)
- Callback query routing
- Conversation state management
- Input validation and sanitization

#### Keyboards.py
UI keyboard layout generation.

**Classes:**
- `Keyboard`: Static keyboard layout methods

**Key Methods:**
- `start_keyboard()`: Main menu
- `monitor_keyboard()`: Monitor mode menu
- `bulk_keyboard()`: Bulk operations menu
- `individual_keyboard()`: Individual operations menu
- `account_management_keyboard()`: Account management menu
- `report_keyboard()`: Report menu

#### Monitor.py
Message monitoring and forwarding system.

**Classes:**
- `Monitor`: Message monitoring handler

**Key Features:**
- Keyword-based message filtering
- Automatic message forwarding
- Channel resolution
- User ignore list support
- Real-time monitoring across accounts

#### actions.py
Bulk and individual operation implementations.

**Classes:**
- `Actions`: Operation execution handler

**Key Operations:**
- Reactions: Apply reactions to messages
- Polls: Vote in polls
- Join/Leave: Group membership management
- Block: User blocking
- Private Messages: Send messages to users
- Comments: Post comments on messages

**Key Features:**
- Bulk operation execution with concurrency control
- Individual account operations
- Automatic retry with exponential backoff
- Rate limiting and flood wait handling
- Session revocation detection and cleanup
- Link parsing and entity resolution

#### Validation.py
Input validation and sanitization.

**Classes:**
- `InputValidator`: Input validation utilities

**Key Features:**
- Phone number validation
- Username validation
- Link validation
- Text sanitization

#### Logger.py
Logging configuration.

**Functions:**
- `setup_logging()`: Configures logging system

**Features:**
- File and console logging
- Log rotation
- Configurable log levels

#### utils.py
General utility functions.

**Key Functions:**
- `get_session_name()`: Extract session name from client
- `cleanup_conversation_state()`: Clean up conversation state
- `execute_bulk_operation()`: Execute bulk operations
- `format_bulk_result_message()`: Format operation results
- `resolve_entity()`: Resolve Telegram entities
- `check_account_exists()`: Check account availability
- `remove_revoked_session_completely()`: Remove revoked sessions

## Configuration Files

### env.example
Template for environment variables. Copy to `.env` and fill in values.

### config.json
Runtime configuration storing:
- Target groups for monitoring
- Keywords for filtering
- Ignore user list
- Client configurations

### clients.json
Client session data and account information.

## Test Structure

### Test Organization

Tests are organized by category:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Flow Tests**: End-to-end user flow testing
- **Edge Case Tests**: Error and boundary condition testing

### Test Files

- `conftest.py`: Pytest fixtures and configuration
- `test_unit_*.py`: Unit tests for specific modules
- `test_flows_*.py`: User flow tests
- `test_integration_*.py`: Integration tests
- `test_*.py`: Feature-specific tests

## Data Flow

1. **User Interaction**: User sends command or clicks button
2. **Handler Processing**: Appropriate handler processes request
3. **Validation**: Input is validated and sanitized
4. **Action Execution**: Operation is executed via Actions class
5. **Client Management**: SessionManager handles account operations
6. **Response**: Result is formatted and sent to user

## Dependencies

### Core Dependencies

- `telethon`: Telegram client library
- `python-dotenv`: Environment variable management
- `aiohttp`: Async HTTP client
- `requests`: HTTP library
- `pysocks`: SOCKS proxy support

### Development Dependencies

- `pytest`: Testing framework
- `pytest-asyncio`: Async test support
- `pytest-cov`: Coverage reporting

## File Naming Conventions

- Module files: `PascalCase.py` for classes, `snake_case.py` for utilities
- Test files: `test_*.py`
- Configuration files: `lowercase.json`, `lowercase.env`
- Documentation: `UPPERCASE.md` for main docs, `lowercase.md` for guides

## Session Files

Session files are stored in the project root with format:
- `{phone_number}.session` for user accounts
- `bot2.session` for bot session

Session files contain authentication data and should never be committed to version control.

