# Project Structure

```
Telegram-Panel/
├── docs/                  # Documentation
├── src/                   # Source code
│   ├── Config.py         # Configuration
│   ├── Telbot.py         # Main bot
│   ├── Client.py         # Account management
│   ├── Handlers.py        # Event handlers
│   ├── Keyboards.py      # UI layouts
│   ├── Monitor.py        # Message monitoring
│   ├── actions.py        # Operations
│   └── Validation.py     # Input validation
├── tests/                 # Test suite
├── main.py               # Entry point
├── requirements.txt      # Dependencies
└── env.example          # Environment template
```

## Key Components

- **Telbot.py**: Main bot orchestrator
- **Handlers.py**: Telegram event handlers
- **actions.py**: Bulk and individual operations
- **Client.py**: Session and account management
- **Monitor.py**: Message monitoring and forwarding
