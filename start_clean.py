#!/usr/bin/env python3
"""
Clean startup script for Telegram bot
Kills existing processes and cleans up session files
"""
import os
import sys
import subprocess
import glob
import time

def cleanup_processes():
    """Kill any existing Python/telethon processes"""
    print("Cleaning up existing processes...")

    try:
        if sys.platform == 'win32':
            # Kill python processes
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/T'],
                         capture_output=True, check=False, timeout=10)
            subprocess.run(['taskkill', '/F', '/IM', 'python3.exe', '/T'],
                         capture_output=True, check=False, timeout=10)
            # Kill any processes with telethon in the name
            subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq *python*'],
                         capture_output=True, check=False, timeout=10)
        else:
            # Unix-like systems
            subprocess.run(['pkill', '-9', '-f', 'python'], capture_output=True, check=False, timeout=10)
    except Exception as e:
        print(f"Warning: Could not kill processes: {e}")

    # Wait for processes to die
    time.sleep(3)

def cleanup_session_files():
    """Remove all session files"""
    print("Cleaning up session files...")

    patterns = ['*.session', '*.db', '*.sqlite', '*.sqlite3']
    for pattern in patterns:
        try:
            files = glob.glob(pattern)
            for file in files:
                try:
                    os.remove(file)
                    print(f"Removed: {file}")
                except OSError as e:
                    print(f"Could not remove {file}: {e}")
        except Exception as e:
            print(f"Error cleaning pattern {pattern}: {e}")

    # Also clean temp directory
    temp_dir = os.environ.get('TEMP', os.environ.get('TMP', '/tmp'))
    for pattern in patterns:
        try:
            temp_files = glob.glob(os.path.join(temp_dir, pattern))
            for file in temp_files:
                try:
                    os.remove(file)
                    print(f"Removed temp file: {file}")
                except OSError:
                    pass
        except Exception as e:
            print(f"Error cleaning temp files: {e}")

def main():
    """Main cleanup and start function"""
    print("=" * 60)
    print("TELEGRAM BOT CLEAN STARTUP")
    print("=" * 60)

    cleanup_processes()
    cleanup_session_files()

    print("Cleanup complete. Starting bot...")
    print("=" * 60)

    # Start the bot
    os.execv(sys.executable, [sys.executable, 'start_bot.py'])

if __name__ == "__main__":
    main()
