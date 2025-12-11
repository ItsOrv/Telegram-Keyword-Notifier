#!/usr/bin/env python3
"""Bot starter with automatic cleanup"""
import os
import asyncio
import logging
import glob
import sys

# Set environment variables directly
os.environ['API_ID'] = '20019286'
os.environ['API_HASH'] = '***REMOVED***'
os.environ['BOT_TOKEN'] = '***REMOVED***'
os.environ['ADMIN_ID'] = '7718839318'
os.environ['CHANNEL_ID'] = 'your_channel_id_or_username'
# No proxy - direct connection
os.environ['PROXY_HOST'] = ''
os.environ['PROXY_PORT'] = '1080'

# Import and run bot
from src.Telbot import TelegramBot
from src.Logger import setup_logging

def cleanup_session_files():
    """Clean up all session files before starting"""
    print("[CLEANUP] Auto-cleaning session files...")

    # First, kill any Python processes that might be holding session files
    try:
        import subprocess
        import sys
        import os
        current_pid = os.getpid()
        print(f"  [KILL] Current process PID: {current_pid}")

        if sys.platform == 'win32':
            # Kill python processes (careful not to kill ourselves)
            print("  [KILL] Terminating other Python processes...")
            # Use a more targeted approach
            try:
                # Get list of python processes and their PIDs
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'],
                                       capture_output=True, text=True, check=False, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'python.exe' in line and 'PID' not in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[1])
                                    if pid != current_pid:
                                        print(f"  [KILL] Terminating PID {pid}")
                                        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                                     capture_output=True, check=False, timeout=5)
                                except (ValueError, IndexError):
                                    pass
            except Exception as e:
                print(f"  [WARN] Could not kill by PID: {e}")
        else:
            # Unix-like systems - exclude current process
            subprocess.run(['pkill', '-f', f'python.*start_bot'], capture_output=True, check=False, timeout=10)
    except Exception as e:
        print(f"  [WARN] Could not kill processes: {e}")

    # Wait a moment for processes to die
    import time
    time.sleep(2)
    print("  [WAIT] Waiting for processes to terminate...")

    patterns = ['*.session', '*.db', '*.sqlite', '*.sqlite3']
    cleaned = 0

    for pattern in patterns:
        try:
            files = glob.glob(pattern)
            for file in files:
                try:
                    os.remove(file)
                    print(f"  [OK] Removed: {file}")
                    cleaned += 1
                except OSError as e:
                    print(f"  [WARN] Could not remove {file}: {e}")
        except Exception as e:
            print(f"  [WARN] Error cleaning pattern {pattern}: {e}")

    # Also clean temp directory
    temp_dir = os.environ.get('TEMP', os.environ.get('TMP', '/tmp'))
    for pattern in patterns:
        try:
            temp_files = glob.glob(os.path.join(temp_dir, pattern))
            for file in temp_files:
                try:
                    os.remove(file)
                    print(f"  [OK] Removed temp file: {file}")
                    cleaned += 1
                except OSError:
                    pass
        except Exception:
            pass

    if cleaned > 0:
        print(f"[CLEANUP] Complete: {cleaned} files removed")
    else:
        print("[CLEANUP] No session files to clean")
    return cleaned

def main():
    try:
        # Always clean up session files on startup
        cleanup_session_files()

        print("[BOT] Starting Telegram Bot...")
        bot = TelegramBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.critical(f"Critical error in main: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    setup_logging()
    main()
