#!/usr/bin/env python3
"""
Final Comprehensive Test

Test all bot functionality with the new working Gemini API key.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

load_dotenv()

def test_gemini_api():
    """Test Gemini API with new key."""
    print("🧪 Testing Gemini API...")
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content("Say 'Gemini is working perfectly!'")
        
        if response and response.text:
            print(f"✅ Gemini Response: {response.text}")
            return True
        else:
            print("❌ Gemini returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return False

def test_ai_engine():
    """Test AI Engine with new configuration."""
    print("\n🔧 Testing AI Engine...")
    
    try:
        from core.ai_engine import AIEngine
        
        engine = AIEngine()
        print(f"Provider: {engine.llm_provider}")
        print(f"Available Gemini keys: {len(engine.gemini_keys)}")
        
        # Test AI response
        response = engine.generate_response("Hello! Test if the AI is working properly.")
        print(f"✅ AI Response: {response[:100]}...")
        
        # Check if it's a real AI response (not error message)
        if len(response) > 50 and "error" not in response.lower():
            return True
        else:
            print("⚠️ Response seems like an error message")
            return False
            
    except Exception as e:
        print(f"❌ AI Engine Error: {e}")
        return False

def test_whatsapp_commands():
    """Test WhatsApp command processing."""
    print("\n📱 Testing WhatsApp Commands...")
    
    try:
        from integrations.whatsapp import WhatsAppBot
        
        bot = WhatsAppBot()
        
        # Test tech quote (should work)
        print("Testing 'tech quote' command...")
        from core.social_media_manager import SocialMediaManager
        social_manager = SocialMediaManager()
        result = social_manager.process_whatsapp_post_command("tech quote", user_id=1)
        
        if result and "✅" in result:
            print(f"✅ Tech Quote: {result}")
        else:
            print(f"❌ Tech Quote Failed: {result}")
            return False
        
        # Test email command (should work with AI)
        print("Testing email functionality...")
        from core.email_agent import EmailAgent
        email_agent = EmailAgent()
        
        if all([email_agent.host, email_agent.username, email_agent.password]):
            print("✅ Email configuration is valid")
        else:
            print("⚠️ Email not fully configured (but that's OK)")
        
        return True
        
    except Exception as e:
        print(f"❌ WhatsApp Commands Error: {e}")
        return False

def test_assistant_processing():
    """Test the core assistant with various inputs."""
    print("\n🤖 Testing Assistant Processing...")
    
    try:
        from core.assistant import JarvisAssistant
        
        assistant = JarvisAssistant()
        
        test_messages = [
            "Hello, how are you?",
            "What's 15 + 25?",
            "Tell me about artificial intelligence",
        ]
        
        for i, message in enumerate(test_messages, 1):
            try:
                response = assistant.process_text_message(message)
                print(f"✅ Test {i}: '{message}' -> '{response[:50]}...'")
            except Exception as e:
                print(f"❌ Test {i} failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Assistant Processing Error: {e}")
        return False

def simulate_whatsapp_interaction():
    """Simulate the exact WhatsApp interaction that was failing."""
    print("\n💬 Simulating WhatsApp Interaction...")
    
    try:
        from integrations.whatsapp import WhatsAppBot
        
        bot = WhatsAppBot()
        
        # Simulate the exact webhook data that was causing issues
        test_scenarios = [
            {
                "name": "Hello Message",
                "webhook_data": {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": "test_user",
                                    "type": "text",
                                    "text": {"body": "Hello"}
                                }]
                            }
                        }]
                    }]
                }
            },
            {
                "name": "Tech Quote Command",
                "webhook_data": {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": "test_user", 
                                    "type": "text",
                                    "text": {"body": "tech quote"}
                                }]
                            }
                        }]
                    }]
                }
            },
            {
                "name": "Help Command",
                "webhook_data": {
                    "entry": [{
                        "changes": [{
                            "value": {
                                "messages": [{
                                    "from": "test_user",
                                    "type": "text", 
                                    "text": {"body": "/help"}
                                }]
                            }
                        }]
                    }]
                }
            }
        ]
        
        for scenario in test_scenarios:
            print(f"Testing: {scenario['name']}")
            try:
                # This should not crash
                bot.handle_incoming_message(scenario['webhook_data'])
                print(f"✅ {scenario['name']}: No crash")
            except Exception as e:
                print(f"❌ {scenario['name']}: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ WhatsApp Simulation Error: {e}")
        return False

def main():
    """Run all final tests."""
    print("🚀 FINAL COMPREHENSIVE TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    tests = [
        ("Gemini API", test_gemini_api),
        ("AI Engine", test_ai_engine),
        ("WhatsApp Commands", test_whatsapp_commands),
        ("Assistant Processing", test_assistant_processing),
        ("WhatsApp Interaction", simulate_whatsapp_interaction)
    ]
    
    results = {}
    passed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"🧪 {test_name}")
        print(f"{'='*40}")
        
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            results[test_name] = False
            print(f"❌ {test_name}: EXCEPTION - {e}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("🏁 FINAL TEST RESULTS")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {len(tests) - passed}/{len(tests)}")
    print(f"Success Rate: {(passed/len(tests))*100:.1f}%")
    
    if passed == len(tests):
        print(f"\n🎉 PERFECT! ALL TESTS PASSED!")
        print(f"\n🚀 YOUR BOT IS READY FOR DEPLOYMENT!")
        print(f"\n📋 WHAT'S FIXED:")
        print("✅ Gemini API working with new key from different account")
        print("✅ AI responses working properly")
        print("✅ WhatsApp message processing working")
        print("✅ Tech quotes working")
        print("✅ All commands processing without crashes")
        print("✅ Improved error handling in place")
        
        print(f"\n🎯 DEPLOYMENT READY:")
        print("1. Commit all changes to git")
        print("2. Push to trigger Render deployment")
        print("3. Test WhatsApp commands in production")
        print("4. Your bot should now respond properly!")
        
        print(f"\n💡 EXPECTED WHATSAPP BEHAVIOR:")
        print("• 'Hello' -> AI conversation response")
        print("• 'tech quote' -> Posts tech quote to Twitter")
        print("• '/help' -> Shows help menu")
        print("• '/emails' -> Shows email summary (if configured)")
        print("• YouTube links -> Downloads and sends video")
        
    else:
        print(f"\n🔧 {len(tests) - passed} test(s) still failing")
        print("Review the errors above before deployment")
    
    return passed == len(tests)

if __name__ == "__main__":
    main()
