#!/usr/bin/env python3
"""
Interactive CLI entry point.
Run with: python interactive_cli.py
"""
import os
import sys
from pathlib import Path

# Ensure we're in the correct directory
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Add src to path
sys.path.insert(0, str(script_dir))

from src.interactive_cli import main

if __name__ == '__main__':
    main()

