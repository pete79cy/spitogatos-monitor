#!/usr/bin/env python3
"""
Test Notification System
Sends a test notification to verify Telegram/Email setup
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spitogatos_monitor import send_telegram_notification, send_email_notification

# Sample test apartment data
TEST_APARTMENTS = [
    {
        'id': 'test_1',
        'title': 'Test Φοιτητικό Studio - Κέντρο Ηρακλείου',
        'price': '350€/μήνα',
        'location': 'Ηράκλειο Κέντρο',
        'size': '35 m²',
        'link': 'https://www.spitogatos.gr/example',
        'found_at': '2026-05-07T06:00:00'
    },
    {
        'id': 'test_2',
        'title': 'Test Διαμέρισμα με μπαλκόνι',
        'price': '400€/μήνα',
        'location': 'Κνωσσός',
        'size': '40 m²',
        'link': 'https://www.spitogatos.gr/example2',
        'found_at': '2026-05-07T06:00:00'
    }
]

def main():
    print("\n" + "="*60)
    print("🧪 Testing Notification System")
    print("="*60 + "\n")
    
    # Check environment variables
    telegram_configured = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
    email_configured = bool(os.getenv("EMAIL_TO") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))
    
    if not telegram_configured and not email_configured:
        print("❌ No notification method configured!")
        print("\nPlease set up at least one of:")
        print("  • Telegram: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        print("  • Email: EMAIL_TO, SMTP_USER, SMTP_PASSWORD")
        print("\nSee README.md for setup instructions")
        return
    
    print("📋 Configuration Status:")
    if telegram_configured:
        print("  ✅ Telegram configured")
    else:
        print("  ⚪ Telegram not configured")
    
    if email_configured:
        print("  ✅ Email configured")
    else:
        print("  ⚪ Email not configured")
    
    print("\n" + "-"*60)
    print("📤 Sending test notifications with sample data...")
    print("-"*60 + "\n")
    
    # Send test notifications
    if telegram_configured:
        print("📱 Sending Telegram test notification...")
        send_telegram_notification(TEST_APARTMENTS)
    
    if email_configured:
        print("📧 Sending Email test notification...")
        send_email_notification(TEST_APARTMENTS)
    
    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60)
    print("\nIf you received the test notifications:")
    print("  • Your setup is working correctly!")
    print("  • You can now run: python spitogatos_monitor.py")
    print("\nIf you didn't receive notifications, check:")
    print("  • Your environment variables are correct")
    print("  • Telegram: bot token and chat ID are valid")
    print("  • Email: SMTP settings and credentials are correct")
    print("  • Email: check your spam folder")
    print("")

if __name__ == "__main__":
    main()
