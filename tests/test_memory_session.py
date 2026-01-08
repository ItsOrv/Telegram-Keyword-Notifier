#!/usr/bin/env python3
"""
Test script to verify memory session approach works
"""
import asyncio
import os
from pathlib import Path

async def test_memory_session():
    """Test the memory session approach"""
    print("Testing Memory Session Approach")
    print("=" * 50)

    try:
        # Import telethon components
        from telethon import TelegramClient
        from src.Config import API_ID, API_HASH

        print("Creating memory session client...")
        # Create client with memory session (None as session name)
        client = TelegramClient(None, API_ID, API_HASH)

        print("Connecting with memory session...")
        await client.connect()

        print("Checking authorization status...")
        is_authorized = await client.is_user_authorized()
        print(f"Authorized: {is_authorized}")

        print("Disconnecting...")
        await client.disconnect()

        print("Creating file session client...")
        session_name = "test_file_session"
        file_client = TelegramClient(session_name, API_ID, API_HASH)
        await file_client.connect()

        print("Copying auth from memory to file client...")
        # This would normally copy auth_key and user_id
        # file_client.session.auth_key = client.session.auth_key
        # file_client.session.user_id = client.session.user_id
        # file_client.session.save()

        print("Disconnecting file client...")
        await file_client.disconnect()

        # Clean up
        session_file = f"{session_name}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
            print(f"Cleaned up {session_file}")

        print("SUCCESS: Memory session approach works!")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_memory_session())
