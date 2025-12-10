#!/usr/bin/env python3
"""Check if Telegram is accessible"""
import socket
import time

def check_telegram_connection():
    """Check if we can connect to Telegram servers"""
    print("Checking Telegram connectivity...")

    # Test connection to Telegram API
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(('149.154.167.51', 443))
        sock.close()

        if result == 0:
            print("✅ CAN connect to Telegram servers")
            return True
        else:
            print("❌ CANNOT connect to Telegram servers")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def check_bot_token():
    """Verify bot token format"""
    token = "***REMOVED***"
    parts = token.split(':')

    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) >= 8:
        print("✅ Bot token format is valid")
        return True
    else:
        print("❌ Bot token format is invalid")
        return False

def main():
    print("=" * 50)
    print("TELEGRAM BOT CONNECTIVITY DIAGNOSIS")
    print("=" * 50)

    # Check bot token
    token_ok = check_bot_token()

    # Check network connection
    network_ok = check_telegram_connection()

    print("\n" + "=" * 50)
    print("DIAGNOSIS RESULTS:")
    print("=" * 50)

    if token_ok and network_ok:
        print("✅ Everything looks good!")
        print("The bot should work when you run it.")
    elif token_ok and not network_ok:
        print("⚠️  Bot token is valid, but network is blocked.")
        print("This is why the bot cannot connect to Telegram.")
        print("\nSOLUTIONS:")
        print("1. Use a VPN (ProtonVPN, ExpressVPN, NordVPN)")
        print("2. Connect to a different network")
        print("3. Use a proxy server")
        print("4. Try mobile hotspot instead of WiFi")
    else:
        print("❌ Configuration issues detected")

    print(f"\nBot Token: {token[:15]}...")
    print(f"Network Access: {'YES' if network_ok else 'BLOCKED'}")

if __name__ == '__main__':
    main()
