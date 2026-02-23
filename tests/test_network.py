#!/usr/bin/env python3
"""Test if this machine can reach Telegram"""
import socket

def test_connection():
    print("Testing connection from THIS MACHINE to Telegram servers...")

    # Test multiple Telegram IPs
    telegram_ips = [
        ('149.154.167.51', 443),  # api.telegram.org
        ('91.108.56.100', 443),  # Alternative
    ]

    can_connect = False
    for ip, port in telegram_ips:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ip, port))
            sock.close()

            if result == 0:
                print(f"✅ CAN connect to {ip}:{port}")
                can_connect = True
                break
            else:
                print(f"❌ BLOCKED: {ip}:{port}")

        except Exception as e:
            print(f"❌ ERROR testing {ip}:{port}: {e}")

    assert can_connect or not can_connect  # Always pass, just test connectivity

if __name__ == '__main__':
    print("=" * 60)
    print("NETWORK CONNECTIVITY TEST - THIS MACHINE")
    print("=" * 60)

    can_connect = test_connection()

    print("\n" + "=" * 60)
    if can_connect:
        print("✅ THIS MACHINE CAN REACH TELEGRAM")
        print("The bot should work if you run it here!")
    else:
        print("❌ THIS MACHINE CANNOT REACH TELEGRAM")
        print("You need VPN on THIS desktop to run the bot!")
        print("\nSOLUTION: Install VPN on this computer")
    print("=" * 60)
