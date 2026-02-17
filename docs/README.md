# Documentation

Complete documentation for Telegram Panel project.

## Documentation Index

### Core Documentation

- **[Project Structure](PROJECT_STRUCTURE.md)**: Detailed project structure and component organization
- **[API Reference](API.md)**: API documentation for core modules and classes

### Guides

- **[Usage Guide](USAGE.md)**: Comprehensive usage instructions and examples

### Additional Resources

- **Main README**: [../README.md](../README.md) - Project overview and quick start
- **Contributing Guide**: [../CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- **Changelog**: [../CHANGELOG.md](../CHANGELOG.md) - Version history

## Module Documentation

### Core Modules

#### Config.py
Configuration management system handling environment variables, JSON configuration files, and runtime settings.

#### Telbot.py
Main bot orchestrator managing client connections, handlers, and bot lifecycle.

#### Client.py
Session management for Telegram accounts including authentication, persistence, and account operations.

#### Handlers.py
Event handlers for Telegram bot interactions including commands, callbacks, and message processing.

#### Keyboards.py
UI keyboard layout generation for interactive bot menus.

#### Monitor.py
Message monitoring system for keyword-based filtering and automatic forwarding.

#### actions.py
Bulk and individual operation implementations for Telegram account actions.

#### Validation.py
Input validation and sanitization utilities.

#### Logger.py
Logging configuration and setup.

#### utils.py
General utility functions for common operations.

## Architecture

The system follows a modular architecture:

1. **Bot Layer**: TelegramBot class orchestrates all components
2. **Handler Layer**: Processes user interactions and commands
3. **Action Layer**: Executes operations on Telegram accounts
4. **Client Layer**: Manages account sessions and connections
5. **Monitor Layer**: Handles message monitoring and forwarding
6. **Config Layer**: Manages configuration and settings

## Design Principles

- **Separation of Concerns**: Each module has a single responsibility
- **Async Operations**: All I/O operations are asynchronous
- **Error Handling**: Comprehensive error handling at all levels
- **Type Safety**: Type hints throughout codebase
- **Testability**: Modular design enables comprehensive testing
