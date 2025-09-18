#!/usr/bin/env python3
"""
Test Reminder System

This script creates a test reminder and checks if it gets sent.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

load_dotenv()

def test_reminder_in_30_seconds():
    """Create a reminder for 30 seconds from now."""
    print("🧪 Creating test reminder for 30 seconds from now...")
    
    try:
        from core.database import DatabaseManager
        from core.scheduler import SchedulerManager
        
        db = DatabaseManager()
        scheduler = SchedulerManager(db)
        scheduler.start()
        
        # Get your WhatsApp number from env
        whatsapp_number = os.getenv('WHATSAPP_DIGEST_TO', '2349022594853')
        
        # Create test user
        user = db.get_or_create_user(
            platform_id=whatsapp_number,
            platform='whatsapp',
            username='test_user'
        )
        
        # Create reminder for 30 seconds from now
        reminder_time = datetime.now() + timedelta(seconds=30)
        
        reminder_data = {
            'user_id': user['id'],
            'title': 'Test Reminder - It Works!',
            'description': 'If you see this, reminders are working correctly!',
            'reminder_time': reminder_time.isoformat(),
            'repeat_pattern': None,
            'platform': 'whatsapp',
            'platform_id': whatsapp_number
        }
        
        result = scheduler.create_reminder(reminder_data)
        
        if result.get('success'):
            print(f"✅ Test reminder created!")
            print(f"📱 Will be sent to: {whatsapp_number}")
            print(f"⏰ Scheduled for: {reminder_time}")
            print(f"⏳ Wait 30 seconds to see if you receive the reminder...")
            
            # Keep the script running for 60 seconds
            print("\n⏳ Waiting for reminder to be sent...")
            for i in range(60):
                time.sleep(1)
                if i == 29:
                    print("🔔 Reminder should be sent now!")
                elif i % 10 == 0 and i > 0:
                    print(f"⏳ {60-i} seconds remaining...")
            
            print("\n✅ Test completed. Check if you received the reminder!")
            
        else:
            print(f"❌ Failed to create test reminder: {result}")
            
    except Exception as e:
        print(f"❌ Test reminder error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reminder_in_30_seconds()
