#!/usr/bin/env python3
"""
Gemini API Quota Monitor

Run this to check your current Gemini API usage and quota status.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def check_gemini_quota():
    """Check Gemini API quota status."""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY not found in .env")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Try a minimal request
        response = model.generate_content("test")
        
        if response and response.text:
            print("✅ Gemini API is working")
            print(f"🕒 Checked at: {datetime.now()}")
            print("💡 Your quota has available requests")
            return True
        else:
            print("⚠️ Gemini API returned empty response")
            return False
            
    except Exception as e:
        error_str = str(e)
        print(f"❌ Gemini API Error: {error_str}")
        
        if "quota" in error_str.lower() or "429" in error_str:
            print("🚫 QUOTA EXCEEDED - This is why your bot is failing!")
            print("⏰ Wait for quota reset (usually 24 hours)")
            print("💰 Consider upgrading to paid plan for higher limits")
            print("🔗 Upgrade at: https://aistudio.google.com/app/apikey")
        
        return False

if __name__ == "__main__":
    print("🔍 Checking Gemini API Quota Status...")
    check_gemini_quota()
