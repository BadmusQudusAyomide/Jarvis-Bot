#!/usr/bin/env python3
"""
Debug script to test AI engine functionality
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

load_dotenv()

def test_ai_engine():
    """Test AI engine functionality."""
    try:
        from core.ai_engine import AIEngine
        
        print("🧠 Testing AI Engine...")
        ai = AIEngine()
        
        print(f"✅ AI Engine initialized with provider: {ai.llm_provider}")
        print(f"📊 Gemini keys available: {len(ai.gemini_keys) if ai.gemini_keys else 0}")
        
        # Test health check
        print("\n🔍 Testing health check...")
        health = ai.health_check()
        print(f"Health check result: {'✅ PASS' if health else '❌ FAIL'}")
        
        # Test simple response
        print("\n💬 Testing response generation...")
        response = ai.generate_response("Hello, how are you?")
        print(f"Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database functionality."""
    try:
        from core.database import DatabaseManager
        
        print("\n🗄️ Testing Database...")
        db = DatabaseManager()
        
        # Test health check
        health = db.health_check()
        print(f"Database health: {'✅ PASS' if health else '❌ FAIL'}")
        
        # Test user creation
        print("\n👤 Testing user operations...")
        user = db.get_or_create_user(
            platform_id="test_user_123",
            platform="telegram",
            username="testuser",
            first_name="Test"
        )
        print(f"User created/retrieved: {user['id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_message_router():
    """Test message router functionality."""
    try:
        from core.database import DatabaseManager
        from core.ai_engine import AIEngine
        from core.scheduler import SchedulerManager
        from core.message_router import MessageRouter
        
        print("\n🔀 Testing Message Router...")
        
        db = DatabaseManager()
        ai = AIEngine()
        scheduler = SchedulerManager(db)
        router = MessageRouter(db, ai, scheduler)
        
        print("✅ Message router initialized")
        
        # Test message processing
        print("\n📨 Testing message processing...")
        message_data = {
            'type': 'text',
            'content': 'Hello Jarvis!',
            'user_info': {
                'username': 'testuser',
                'first_name': 'Test'
            }
        }
        
        response = router.process_message(
            platform='telegram',
            platform_user_id='test_user_123',
            message_data=message_data
        )
        
        print(f"Response type: {response.get('type')}")
        print(f"Response content: {response.get('content', '')[:100]}...")
        print(f"Success: {'✅ PASS' if response.get('success', True) else '❌ FAIL'}")
        
        return response.get('success', True)
        
    except Exception as e:
        print(f"❌ Message router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_telegram_webhook():
    """Test Telegram webhook functionality."""
    try:
        from integrations.telegram_webhook import TelegramWebhook
        from core.database import DatabaseManager
        from core.ai_engine import AIEngine
        from core.scheduler import SchedulerManager
        from core.message_router import MessageRouter
        
        print("\n📱 Testing Telegram Webhook...")
        
        # Initialize components
        db = DatabaseManager()
        ai = AIEngine()
        scheduler = SchedulerManager(db)
        router = MessageRouter(db, ai, scheduler)
        webhook = TelegramWebhook(router)
        
        print("✅ Telegram webhook initialized")
        
        # Test webhook processing
        print("\n📨 Testing webhook message processing...")
        update_data = {
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456,
                    "first_name": "Test",
                    "username": "testuser"
                },
                "chat": {
                    "id": 123456
                },
                "text": "Hello Jarvis!"
            }
        }
        
        result = webhook.handle_update(update_data)
        print(f"Webhook result: {result}")
        
        return result.get('status') == 'processed'
        
    except Exception as e:
        print(f"❌ Telegram webhook test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🤖 Jarvis Bot Debug Tests")
    print("=" * 50)
    
    tests = [
        ("AI Engine", test_ai_engine),
        ("Database", test_database),
        ("Message Router", test_message_router),
        ("Telegram Webhook", test_telegram_webhook)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\n🔧 Issues found! Check the error messages above.")
    else:
        print("\n🎉 All systems working! The issue might be in deployment environment.")

if __name__ == "__main__":
    main()
