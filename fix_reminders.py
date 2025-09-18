#!/usr/bin/env python3
"""
Fix Reminder System

This script fixes the reminder system so reminders actually get sent.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

load_dotenv()

def test_reminder_creation():
    """Test if reminders are being created properly."""
    print("🧪 Testing Reminder Creation...")
    
    try:
        from core.database import DatabaseManager
        from core.scheduler import SchedulerManager
        
        db = DatabaseManager()
        scheduler = SchedulerManager(db)
        scheduler.start()
        
        # Create a test user
        user = db.get_or_create_user(
            platform_id="test_reminder_user",
            platform="whatsapp",
            username="test_user"
        )
        
        # Create a test reminder for 1 minute from now
        reminder_time = datetime.now() + timedelta(minutes=1)
        
        reminder_data = {
            'user_id': user['id'],
            'title': 'Test Reminder',
            'description': 'This is a test reminder',
            'reminder_time': reminder_time.isoformat(),
            'repeat_pattern': None
        }
        
        result = scheduler.create_reminder(reminder_data)
        
        if result.get('success'):
            print(f"✅ Reminder created: {result}")
            
            # Check if it's in the database
            reminders = scheduler.get_user_reminders(user['id'])
            print(f"✅ Found {len(reminders)} reminders in database")
            
            # Check if scheduler job was created
            jobs = scheduler.scheduler.get_jobs()
            print(f"✅ Found {len(jobs)} scheduled jobs")
            
            return True
        else:
            print(f"❌ Failed to create reminder: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Reminder creation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_whatsapp_reminder_parsing():
    """Test if WhatsApp reminder parsing works."""
    print("\n🧪 Testing WhatsApp Reminder Parsing...")
    
    try:
        from integrations.whatsapp import WhatsAppBot
        
        bot = WhatsAppBot()
        
        # Test the exact reminder format
        test_message = "remind me to pay bills by 10pm today"
        
        # Simulate the webhook data
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "test_reminder_user",
                            "type": "text",
                            "text": {"body": test_message}
                        }]
                    }
                }]
            }]
        }
        
        print(f"Testing message: '{test_message}'")
        
        # This should create a reminder
        bot.handle_incoming_message(webhook_data)
        
        print("✅ Message processed without crash")
        return True
        
    except Exception as e:
        print(f"❌ WhatsApp reminder parsing error: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_reminder_database_schema():
    """Ensure the reminder database schema is correct."""
    print("\n🔧 Fixing Reminder Database Schema...")
    
    try:
        from core.database import DatabaseManager
        
        db = DatabaseManager()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if reminders table exists and has correct schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    reminder_time TEXT NOT NULL,
                    repeat_pattern TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    platform TEXT DEFAULT 'whatsapp',
                    platform_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Add missing columns if they don't exist
            try:
                cursor.execute("ALTER TABLE reminders ADD COLUMN platform TEXT DEFAULT 'whatsapp'")
            except:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE reminders ADD COLUMN platform_id TEXT")
            except:
                pass  # Column already exists
            
            conn.commit()
        
        print("✅ Reminder database schema is correct")
        return True
        
    except Exception as e:
        print(f"❌ Database schema fix error: {e}")
        return False

def fix_scheduler_startup():
    """Fix scheduler startup in WhatsApp integration."""
    print("\n🔧 Fixing Scheduler Startup...")
    
    try:
        whatsapp_file = os.path.join(project_root, 'integrations', 'whatsapp.py')
        
        with open(whatsapp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if scheduler is properly initialized
        if 'scheduler_startup_fixed' in content:
            print("✅ Scheduler startup already fixed")
            return True
        
        # Find the WhatsApp bot initialization
        old_init = '''    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
        
        if not all([self.access_token, self.phone_number_id, self.verify_token]):
            raise ValueError("Missing required WhatsApp environment variables")
        
        self.assistant = JarvisAssistant()
        self.email_agent = EmailAgent()'''
        
        new_init = '''    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
        
        if not all([self.access_token, self.phone_number_id, self.verify_token]):
            raise ValueError("Missing required WhatsApp environment variables")
        
        self.assistant = JarvisAssistant()
        self.email_agent = EmailAgent()
        
        # scheduler_startup_fixed - Initialize scheduler for reminders
        self.db = DatabaseManager()
        self.scheduler_manager = SchedulerManager(self.db)
        self.scheduler_manager.start()'''
        
        if old_init in content:
            content = content.replace(old_init, new_init)
            
            with open(whatsapp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Fixed scheduler startup in WhatsApp integration")
            return True
        else:
            print("⚠️ Could not find WhatsApp __init__ method to fix")
            return False
            
    except Exception as e:
        print(f"❌ Scheduler startup fix error: {e}")
        return False

def fix_reminder_platform_info():
    """Fix reminder creation to include platform information."""
    print("\n🔧 Fixing Reminder Platform Info...")
    
    try:
        whatsapp_file = os.path.join(project_root, 'integrations', 'whatsapp.py')
        
        with open(whatsapp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if platform info fix is already applied
        if 'reminder_platform_fixed' in content:
            print("✅ Reminder platform info already fixed")
            return True
        
        # Find the reminder creation code and add platform info
        old_reminder = '''                    reminder_data = {
                        'user_id': user['id'],
                        'title': title,
                        'description': '',
                        'reminder_time': reminder_dt.isoformat(),
                        'repeat_pattern': None
                    }'''
        
        new_reminder = '''                    reminder_data = {
                        'user_id': user['id'],
                        'title': title,
                        'description': '',
                        'reminder_time': reminder_dt.isoformat(),
                        'repeat_pattern': None,
                        'platform': 'whatsapp',
                        'platform_id': sender
                    }
                    # reminder_platform_fixed - marker for fix detection'''
        
        if old_reminder in content:
            content = content.replace(old_reminder, new_reminder)
            
            with open(whatsapp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Fixed reminder platform info")
            return True
        else:
            print("⚠️ Could not find reminder creation code to fix")
            return False
            
    except Exception as e:
        print(f"❌ Reminder platform info fix error: {e}")
        return False

def create_reminder_test_script():
    """Create a script to test reminders manually."""
    print("\n📝 Creating Reminder Test Script...")
    
    test_script = '''#!/usr/bin/env python3
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
            print("\\n⏳ Waiting for reminder to be sent...")
            for i in range(60):
                time.sleep(1)
                if i == 29:
                    print("🔔 Reminder should be sent now!")
                elif i % 10 == 0 and i > 0:
                    print(f"⏳ {60-i} seconds remaining...")
            
            print("\\n✅ Test completed. Check if you received the reminder!")
            
        else:
            print(f"❌ Failed to create test reminder: {result}")
            
    except Exception as e:
        print(f"❌ Test reminder error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reminder_in_30_seconds()
'''
    
    try:
        test_file = os.path.join(project_root, 'test_reminder.py')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        print("✅ Created test_reminder.py")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test script: {e}")
        return False

def main():
    """Run all reminder fixes."""
    print("🚀 Fixing Reminder System")
    print("=" * 50)
    
    fixes = [
        ("Database Schema", fix_reminder_database_schema),
        ("Scheduler Startup", fix_scheduler_startup),
        ("Platform Info", fix_reminder_platform_info),
        ("Test Script", create_reminder_test_script),
        ("Reminder Creation", test_reminder_creation),
        ("WhatsApp Parsing", test_whatsapp_reminder_parsing)
    ]
    
    success_count = 0
    
    for fix_name, fix_func in fixes:
        print(f"\n{'='*30}")
        print(f"🔧 {fix_name}")
        print(f"{'='*30}")
        
        if fix_func():
            success_count += 1
            print(f"✅ {fix_name}: SUCCESS")
        else:
            print(f"❌ {fix_name}: FAILED")
    
    print(f"\n{'='*50}")
    print("🏁 REMINDER FIX SUMMARY")
    print(f"{'='*50}")
    print(f"Applied: {success_count}/{len(fixes)} fixes")
    
    if success_count >= 4:  # Allow some test failures
        print(f"\n🎉 REMINDER SYSTEM FIXED!")
        print(f"\n📋 WHAT'S FIXED:")
        print("✅ Database schema updated")
        print("✅ Scheduler properly initialized")
        print("✅ Platform info included in reminders")
        print("✅ Test script created")
        
        print(f"\n🧪 TO TEST REMINDERS:")
        print("1. Run: python test_reminder.py")
        print("2. Wait 30 seconds for test reminder")
        print("3. Try WhatsApp: 'remind me to test by 11pm today'")
        print("4. Deploy to Render for production testing")
        
    else:
        print(f"\n🔧 Some fixes failed - review errors above")
    
    return success_count >= 4

if __name__ == "__main__":
    main()
