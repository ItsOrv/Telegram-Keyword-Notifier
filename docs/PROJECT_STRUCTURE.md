# Project Structure

```
Telegram-Panel/
├── .github/
│   └── workflows/
│       └── python-app.yml      # CI/CD pipeline
├── docs/                        # Documentation and reports
│   └── README.md               # Documentation index
├── src/                         # Source code
│   ├── Config.py               # Configuration management
│   ├── Telbot.py               # Main bot class
│   ├── Client.py               # Account/session management
│   ├── Handlers.py             # Event handlers
│   ├── Keyboards.py            # Keyboard layouts
│   ├── Monitor.py              # Message monitoring
│   ├── actions.py              # Bulk/individual actions
│   ├── Validation.py           # Input validation
│   └── Logger.py               # Logging setup
├── tests/                       # Test suite
│   ├── test_unit_*.py          # Unit tests
│   ├── test_flows_*.py         # Flow tests
│   ├── test_integration_*.py   # Integration tests
│   ├── conftest.py             # Pytest configuration
│   └── run_tests.py            # Test runner
├── .editorconfig               # Editor configuration
├── .gitignore                  # Git ignore rules
├── CHANGELOG.md                # Version history
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # License file
├── README.md                   # Main documentation
├── requirements.txt            # Python dependencies
├── env.example                 # Environment variables template
├── install.sh                  # Installation script
└── main.py                     # Application entry point
```

## Key Files

- **main.py**: Entry point for the application
- **src/Telbot.py**: Main bot class that orchestrates all components
- **src/Handlers.py**: Handles all Telegram events (commands, callbacks, messages)
- **src/actions.py**: Implements all bulk and individual operations
- **src/Client.py**: Manages Telegram client sessions
- **src/Monitor.py**: Monitors messages and forwards based on keywords

## Testing

All tests are located in the `tests/` directory:
- Unit tests: Test individual components
- Flow tests: Test complete user workflows
- Integration tests: Test component interactions

Run tests with: `pytest tests/`

