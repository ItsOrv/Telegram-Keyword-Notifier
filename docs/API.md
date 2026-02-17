# API Reference

Complete API documentation for Telegram Panel modules.

## Config Module

### ConfigManager

Manages JSON configuration files with loading, saving, and merging capabilities.

#### Methods

**`__init__(filename: str, config: Optional[Dict[str, Any]] = None)`**
- Initialize ConfigManager with configuration file path
- Parameters:
  - `filename`: Path to configuration file
  - `config`: Optional initial configuration dictionary

#### Methods

**`load_config() -> Dict[str, Any]`**
- Load configuration from JSON file
- Returns default configuration if file doesn't exist or is invalid
- Returns: Configuration dictionary

**`save_config(config: Dict[str, Any]) -> None`**
- Save configuration to JSON file
- Parameters:
  - `config`: Configuration dictionary to save

**`update_config(key: str, value: Any) -> None`**
- Update specific configuration key and save
- Parameters:
  - `key`: Configuration key to update
  - `value`: New value for key

**`merge_config(new_config: Dict[str, Any]) -> None`**
- Merge new configuration with existing configuration
- Parameters:
  - `new_config`: Dictionary containing configuration updates

**`get_config(key: Optional[str] = None) -> Union[Dict[str, Any], Any]`**
- Retrieve configuration value or entire configuration
- Parameters:
  - `key`: Optional configuration key
- Returns: Configuration value or full dictionary

### Environment Functions

**`validate_env_file() -> None`**
- Validate all required environment variables are set
- Raises ValueError if any required variable is missing

**`get_env_variable(name: str, default: Optional[Any] = None) -> Any`**
- Retrieve environment variable with optional default
- Parameters:
  - `name`: Environment variable name
  - `default`: Default value if not set
- Returns: Environment variable value or default

**`get_env_int(name: str, default: int = 0) -> int`**
- Retrieve environment variable as integer
- Parameters:
  - `name`: Environment variable name
  - `default`: Default integer value
- Returns: Integer value or default

## Telbot Module

### TelegramBot

Main bot orchestrator managing all system components.

#### Methods

**`__init__()`**
- Initialize TelegramBot with all components
- Sets up configuration, handlers, and managers

**`async start()`**
- Start bot and initialize all components
- Validates environment configuration
- Connects to Telegram
- Initializes handlers and clients
- Sends admin notification

**`async run()`**
- Run bot main loop
- Handles bot lifecycle and shutdown

**`async init_handlers()`**
- Initialize and register all event handlers
- Sets up command, callback, and message handlers

**`async notify_admin(message: str) -> None`**
- Send notification message to admin
- Parameters:
  - `message`: Message text to send

## Client Module

### SessionManager

Manages Telegram client sessions and account operations.

#### Methods

**`__init__(config, active_clients, tbot)`**
- Initialize SessionManager
- Parameters:
  - `config`: Configuration dictionary
  - `active_clients`: Dictionary of active clients
  - `tbot`: Telegram bot instance

**`async detect_sessions()`**
- Detect and load Telegram client sessions from configuration
- Adds sessions to active_clients if not already active

**`async start_saved_clients()`**
- Start all saved client sessions
- Handles authentication and connection

**`async add_client(phone_number: str, event) -> bool`**
- Add new client session
- Parameters:
  - `phone_number`: Phone number for account
  - `event`: Telegram event for interaction
- Returns: True if successful

**`async check_report_status(phone_number: str, account) -> bool`**
- Check if account has active reports
- Parameters:
  - `phone_number`: Account phone number
  - `account`: TelegramClient instance
- Returns: True if account has reports

### AccountHandler

Handles account-related operations and UI interactions.

#### Methods

**`async add_account(event)`**
- Handle account addition flow
- Parameters:
  - `event`: Telegram event

**`async show_accounts(event)`**
- Display list of all accounts
- Parameters:
  - `event`: Telegram event

**`async update_groups(event)`**
- Update groups list for all accounts
- Parameters:
  - `event`: Telegram event

## Handlers Module

### CommandHandler

Handles bot commands.

#### Methods

**`async start_command(event)`**
- Handle /start command
- Displays main menu keyboard
- Parameters:
  - `event`: Telegram NewMessage event

### CallbackHandler

Handles callback queries from inline keyboards.

#### Methods

**`__init__(tbot)`**
- Initialize CallbackHandler with bot instance
- Sets up sub-handlers and actions

**`async handle_callback(event)`**
- Route callback queries to appropriate handlers
- Parameters:
  - `event`: Telegram CallbackQuery event

### MessageHandler

Handles text messages and conversation flows.

#### Methods

**`async handle_message(event)`**
- Process incoming text messages
- Manages conversation state
- Parameters:
  - `event`: Telegram NewMessage event

## Actions Module

### Actions

Handles bulk and individual operations for Telegram accounts.

#### Methods

**`__init__(tbot)`**
- Initialize Actions class
- Parameters:
  - `tbot`: TelegramBot instance

**`async _execute_bulk_operation(accounts, operation_func, operation_name) -> Tuple[int, int, List[str]]`**
- Execute bulk operation across multiple accounts
- Parameters:
  - `accounts`: List of TelegramClient instances
  - `operation_func`: Async function to execute
  - `operation_name`: Name for logging
- Returns: Tuple of (success_count, error_count, revoked_sessions)

**`async _execute_with_retry(operation, account, max_retries=3, operation_name="operation") -> Tuple[bool, Exception]`**
- Execute operation with automatic retry
- Parameters:
  - `operation`: Async callable to execute
  - `account`: TelegramClient instance
  - `max_retries`: Maximum retry attempts
  - `operation_name`: Name for logging
- Returns: Tuple of (success, error)

**`async parse_telegram_link(link: str, account=None) -> Tuple[Any, int]`**
- Parse Telegram link to extract entity and message ID
- Parameters:
  - `link`: Telegram message link
  - `account`: Optional TelegramClient for username resolution
- Returns: Tuple of (entity, message_id) or (None, None)

### Bulk Operations

**`async bulk_reaction(event, num_accounts)`**
- Apply reaction to message using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

**`async bulk_poll(event, num_accounts)`**
- Vote in poll using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

**`async bulk_join(event, num_accounts)`**
- Join group/channel using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

**`async bulk_leave(event, num_accounts)`**
- Leave group/channel using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

**`async bulk_block(event, num_accounts)`**
- Block user using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

**`async bulk_send_pv(event, num_accounts)`**
- Send private message using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

**`async bulk_comment(event, num_accounts)`**
- Post comment on message using multiple accounts
- Parameters:
  - `event`: Telegram event
  - `num_accounts`: Number of accounts to use

### Individual Operations

**`async reaction(account, event)`**
- Apply reaction using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

**`async poll(account, event)`**
- Vote in poll using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

**`async join(account, event)`**
- Join group/channel using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

**`async left(account, event)`**
- Leave group/channel using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

**`async block(account, event)`**
- Block user using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

**`async send_pv(account, event)`**
- Send private message using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

**`async comment(account, event)`**
- Post comment using single account
- Parameters:
  - `account`: TelegramClient instance
  - `event`: Telegram event

## Monitor Module

### Monitor

Handles message monitoring and forwarding.

#### Methods

**`__init__(tbot)`**
- Initialize Monitor class
- Parameters:
  - `tbot`: TelegramBot instance

**`async resolve_channel_id() -> None`**
- Resolve CHANNEL_ID to numeric ID if username provided
- Caches resolved ID for subsequent use

**`async start_monitoring() -> None`**
- Start monitoring messages from all active accounts
- Sets up event handlers for message filtering

**`async stop_monitoring() -> None`**
- Stop message monitoring
- Removes event handlers

## Keyboards Module

### Keyboard

Provides static methods for generating inline keyboard layouts.

#### Methods

**`start_keyboard() -> List[List[Button]]`**
- Generate main start menu keyboard
- Returns: List of button rows

**`monitor_keyboard() -> List[List[Button]]`**
- Generate monitor mode keyboard
- Returns: List of button rows

**`bulk_keyboard() -> List[List[Button]]`**
- Generate bulk operations keyboard
- Returns: List of button rows

**`individual_keyboard() -> List[List[Button]]`**
- Generate individual operations keyboard
- Returns: List of button rows

**`account_management_keyboard() -> List[List[Button]]`**
- Generate account management keyboard
- Returns: List of button rows

**`report_keyboard() -> List[List[Button]]`**
- Generate report menu keyboard
- Returns: List of button rows

**`add_cancel_button(buttons: List[List[Button]]) -> List[List[Button]]`**
- Add cancel button to keyboard
- Parameters:
  - `buttons`: Existing button rows
- Returns: Updated button rows with cancel button

## Validation Module

### InputValidator

Provides input validation utilities.

#### Methods

**`validate_phone(phone: str) -> bool`**
- Validate phone number format
- Parameters:
  - `phone`: Phone number string
- Returns: True if valid

**`validate_username(username: str) -> bool`**
- Validate Telegram username format
- Parameters:
  - `username`: Username string
- Returns: True if valid

**`validate_link(link: str) -> bool`**
- Validate Telegram link format
- Parameters:
  - `link`: Link string
- Returns: True if valid

## Utils Module

### Utility Functions

**`get_session_name(client) -> str`**
- Extract session name from TelegramClient
- Parameters:
  - `client`: TelegramClient instance
- Returns: Session name string

**`async cleanup_conversation_state(tbot, user_id: int) -> None`**
- Clean up conversation state for user
- Parameters:
  - `tbot`: TelegramBot instance
  - `user_id`: User ID

**`async execute_bulk_operation(accounts, operation_func, operation_name) -> Tuple[int, int, List[str]]`**
- Execute bulk operation with error handling
- Parameters:
  - `accounts`: List of TelegramClient instances
  - `operation_func`: Async function to execute
  - `operation_name`: Name for logging
- Returns: Tuple of (success_count, error_count, revoked_sessions)

**`format_bulk_result_message(operation_name: str, success: int, errors: int, revoked: List[str]) -> str`**
- Format bulk operation result message
- Parameters:
  - `operation_name`: Operation name
  - `success`: Success count
  - `errors`: Error count
  - `revoked`: List of revoked session names
- Returns: Formatted message string

**`async resolve_entity(client, identifier) -> Any`**
- Resolve Telegram entity from identifier
- Parameters:
  - `client`: TelegramClient instance
  - `identifier`: Entity identifier (username, ID, etc.)
- Returns: Telegram entity

**`async check_account_exists(tbot, session_name: str) -> bool`**
- Check if account exists in active clients
- Parameters:
  - `tbot`: TelegramBot instance
  - `session_name`: Session name
- Returns: True if account exists

**`async remove_revoked_session_completely(tbot, session_name: str) -> None`**
- Remove revoked session completely
- Parameters:
  - `tbot`: TelegramBot instance
  - `session_name`: Session name to remove

