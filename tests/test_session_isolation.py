#!/usr/bin/env python3
"""
Test script to verify session isolation works
"""
import os
import tempfile
import shutil
from pathlib import Path

def test_session_isolation():
    """Test the session isolation logic"""
    print("Testing Session Isolation Logic")
    print("=" * 50)

    # Simulate the isolation logic
    temp_base = tempfile.gettempdir()
    session_dir = os.path.join(temp_base, f"telethon_sessions_test_{os.getpid()}")
    os.makedirs(session_dir, exist_ok=True)

    print(f"Created temp session directory: {session_dir}")

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(session_dir)
    print(f"Changed to temp directory: {session_dir}")

    # Create a test session file
    test_session = "test_session.session"
    with open(test_session, 'w') as f:
        f.write("test data")

    print(f"Created test session file: {test_session}")

    # Move it back to original directory
    target_file = os.path.join(original_cwd, "moved_session.session")
    shutil.move(test_session, target_file)
    print(f"Moved session file to: {target_file}")

    # Change back to original directory
    os.chdir(original_cwd)
    print(f"Changed back to original directory: {original_cwd}")

    # Clean up temp directory
    shutil.rmtree(session_dir)
    print("Cleaned up temp session directory")

    # Verify the file was moved
    if os.path.exists(target_file):
        print("SUCCESS: Session file successfully moved!")
        os.remove(target_file)  # Clean up
    else:
        print("FAILED: Session file was not moved properly")

    print("=" * 50)
    print("Session isolation test completed!")

if __name__ == "__main__":
    test_session_isolation()
