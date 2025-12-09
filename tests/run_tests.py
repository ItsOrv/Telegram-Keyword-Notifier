#!/usr/bin/env python3
"""
Script to run all tests and generate comprehensive test report
"""
import subprocess
import sys
import os


def run_tests():
    """Run all tests and display results"""
    print("=" * 70)
    print("🧪 اجرای تست‌های جامع Telegram Panel Bot")
    print("=" * 70)
    print()
    
    # Change to project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Run tests with coverage
    print("📊 در حال اجرای تست‌ها با coverage...")
    print()
    
    result = subprocess.run([
        "pytest", 
        "tests/",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--tb=short"
    ])
    
    print()
    print("=" * 70)
    if result.returncode == 0:
        print("✅ تمام تست‌ها با موفقیت پاس شدند!")
        print()
        print("📄 گزارش HTML coverage در htmlcov/index.html قابل مشاهده است.")
    else:
        print("❌ برخی تست‌ها ناموفق بودند. لطفاً خروجی بالا را بررسی کنید.")
    print("=" * 70)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())

