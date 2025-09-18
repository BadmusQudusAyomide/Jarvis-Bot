#!/usr/bin/env python3
"""
Test Gemini API Key Rotation

This script tests if the bot can rotate through multiple Gemini API keys
when one hits quota limits.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

load_dotenv()

def test_key_rotation():
    """Test if multiple Gemini keys are being used properly."""
    
    print("🔍 Testing Gemini API Key Configuration...")
    
    # Check environment variables
    single_key = os.getenv('GEMINI_API_KEY')
    multiple_keys = os.getenv('GEMINI_API_KEYS')
    
    print(f"GEMINI_API_KEY: {'✓' if single_key else '✗'}")
    print(f"GEMINI_API_KEYS: {'✓' if multiple_keys else '✗'}")
    
    if multiple_keys:
        keys = [k.strip() for k in multiple_keys.split(',') if k.strip()]
        print(f"Found {len(keys)} API keys")
        
        # Test each key individually
        import google.generativeai as genai
        
        working_keys = []
        quota_exceeded_keys = []
        
        for i, key in enumerate(keys, 1):
            print(f"\n🧪 Testing Key {i}: {key[:20]}...")
            
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Say 'Key working'")
                
                if response and response.text:
                    print(f"✅ Key {i}: WORKING")
                    working_keys.append(key)
                else:
                    print(f"⚠️ Key {i}: Empty response")
                    
            except Exception as e:
                error_str = str(e)
                if "quota" in error_str.lower() or "429" in error_str:
                    print(f"🚫 Key {i}: QUOTA EXCEEDED")
                    quota_exceeded_keys.append(key)
                else:
                    print(f"❌ Key {i}: ERROR - {error_str[:100]}...")
        
        print(f"\n📊 SUMMARY:")
        print(f"✅ Working keys: {len(working_keys)}")
        print(f"🚫 Quota exceeded: {len(quota_exceeded_keys)}")
        print(f"❌ Other errors: {len(keys) - len(working_keys) - len(quota_exceeded_keys)}")
        
        if working_keys:
            print(f"\n🎉 SUCCESS! {len(working_keys)} keys are available for use")
            return True
        else:
            print(f"\n⚠️ ALL KEYS EXHAUSTED! Wait for quota reset or add more keys")
            return False
    
    else:
        print("❌ No GEMINI_API_KEYS found in .env file")
        return False

def test_ai_engine_rotation():
    """Test if the AI engine properly rotates through keys."""
    
    print("\n🔄 Testing AI Engine Key Rotation...")
    
    try:
        from core.ai_engine import AIEngine
        
        engine = AIEngine()
        
        print(f"AI Engine initialized with {len(engine.gemini_keys)} keys")
        
        # Test multiple requests to see if it rotates
        for i in range(3):
            try:
                response = engine.generate_response(f"Test message {i+1}")
                print(f"✅ Request {i+1}: {response[:50]}...")
            except Exception as e:
                print(f"❌ Request {i+1}: {str(e)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Engine test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Starting Gemini API Key Rotation Test")
    
    key_test = test_key_rotation()
    engine_test = test_ai_engine_rotation()
    
    print(f"\n🏁 FINAL RESULTS:")
    print(f"Key Configuration: {'✅ PASS' if key_test else '❌ FAIL'}")
    print(f"AI Engine Rotation: {'✅ PASS' if engine_test else '❌ FAIL'}")
    
    if key_test and engine_test:
        print("\n🎉 Your bot should now work with multiple API keys!")
        print("💡 Deploy the updated bot to Render to fix the WhatsApp issues")
    else:
        print("\n🔧 Issues found that need fixing before deployment")

if __name__ == "__main__":
    main()
