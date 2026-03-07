#!/usr/bin/env python3
"""
CLI entry point for Telegram Panel.
Run operations without Telegram bot.
"""
import os
import sys
from pathlib import Path

# Ensure we're in the correct directory
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Add src to path
sys.path.insert(0, str(script_dir))

from src.cli import main

if __name__ == '__main__':
    main()

