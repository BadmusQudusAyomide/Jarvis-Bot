#!/usr/bin/env python3
"""
WhatsApp Webhook Setup Script

This script helps set up the WhatsApp Business API webhook to point to your deployed application.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_whatsapp_webhook():
    """Set up WhatsApp Business API webhook."""
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    webhook_url = "https://jarvis-bot-ftpp.onrender.com/webhook/whatsapp"
    verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'jarvis_webhook_2024')
    
    if not access_token or not phone_number_id:
        print("❌ WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not found in .env file")
        return False
    
    # WhatsApp webhook configuration endpoint
    api_url = f"https://graph.facebook.com/v18.0/{phone_number_id}/webhooks"
    
    payload = {
        "webhook_url": webhook_url,
        "verify_token": verify_token,
        "subscribed_fields": ["messages", "message_deliveries", "message_reads"]
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print(f"🔗 Setting WhatsApp webhook to: {webhook_url}")
    print(f"📱 Phone Number ID: {phone_number_id}")
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            print("✅ WhatsApp webhook set successfully!")
            print(f"📋 Response: {result}")
            return True
        else:
            print(f"❌ Failed to set WhatsApp webhook:")
            print(f"Status: {response.status_code}")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting WhatsApp webhook: {e}")
        return False

def get_whatsapp_webhook_info():
    """Get current WhatsApp webhook information."""
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        print("❌ WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not found in .env file")
        return
    
    api_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(api_url, headers=headers)
        result = response.json()
        
        if response.status_code == 200:
            print("\n📊 WhatsApp Business Account Info:")
            print(f"📱 Phone Number: {result.get('display_phone_number', 'Unknown')}")
            print(f"🆔 Phone Number ID: {result.get('id', 'Unknown')}")
            print(f"✅ Status: {result.get('verified_name', 'Unknown')}")
            
            # Try to get webhook info (this might not be directly available)
            print(f"\n🔗 Webhook should be pointing to: https://jarvis-bot-ftpp.onrender.com/webhook/whatsapp")
        else:
            print(f"❌ Failed to get WhatsApp info: {result}")
            
    except Exception as e:
        print(f"❌ Error getting WhatsApp info: {e}")

def test_whatsapp_api():
    """Test WhatsApp API connection."""
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        print("❌ WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not found in .env file")
        return False
    
    # Test API by getting phone number info
    api_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(api_url, headers=headers)
        result = response.json()
        
        if response.status_code == 200:
            print(f"✅ WhatsApp API is working!")
            print(f"📱 Business Phone: {result.get('display_phone_number')}")
            print(f"🏢 Business Name: {result.get('verified_name')}")
            return True
        else:
            print(f"❌ WhatsApp API test failed:")
            print(f"Status: {response.status_code}")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing WhatsApp API: {e}")
        return False

def verify_webhook_manually():
    """Manually verify the webhook endpoint."""
    webhook_url = "https://jarvis-bot-ftpp.onrender.com/webhook/whatsapp"
    verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'jarvis_webhook_2024')
    
    # Simulate WhatsApp verification request
    params = {
        'hub.mode': 'subscribe',
        'hub.verify_token': verify_token,
        'hub.challenge': 'test_challenge_123'
    }
    
    try:
        print(f"🔍 Testing webhook verification at: {webhook_url}")
        response = requests.get(webhook_url, params=params)
        
        if response.status_code == 200:
            print("✅ Webhook verification successful!")
            print(f"Response: {response.text}")
            return True
        else:
            print(f"❌ Webhook verification failed:")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        return False

def main():
    """Main function."""
    print("📱 WhatsApp Business API Webhook Setup")
    print("=" * 50)
    
    # Test API connection first
    print("\n1️⃣ Testing WhatsApp API connection...")
    if not test_whatsapp_api():
        print("\n❌ WhatsApp API connection failed. Please check your credentials.")
        return
    
    # Get current info
    print("\n2️⃣ Getting current WhatsApp info...")
    get_whatsapp_webhook_info()
    
    # Test webhook verification
    print("\n3️⃣ Testing webhook verification...")
    verify_webhook_manually()
    
    # Ask user what to do
    print("\n4️⃣ What would you like to do?")
    print("1. Set up webhook (configure WhatsApp to send messages to your app)")
    print("2. Just check current status")
    print("3. Show setup instructions")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        print("\n🔧 Setting up WhatsApp webhook...")
        print("\n⚠️  Note: WhatsApp webhook setup requires additional configuration")
        print("in the Meta Developer Console. This script shows you what to do.")
        
        webhook_url = "https://jarvis-bot-ftpp.onrender.com/webhook/whatsapp"
        verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'jarvis_webhook_2024')
        
        print(f"\n📋 Manual Setup Instructions:")
        print(f"1. Go to: https://developers.facebook.com/apps")
        print(f"2. Select your WhatsApp Business app")
        print(f"3. Go to WhatsApp > Configuration")
        print(f"4. In the Webhook section, click 'Edit'")
        print(f"5. Set Callback URL to: {webhook_url}")
        print(f"6. Set Verify Token to: {verify_token}")
        print(f"7. Subscribe to: messages, message_deliveries, message_reads")
        print(f"8. Click 'Verify and Save'")
        
        print(f"\n✅ Your webhook endpoint is ready at: {webhook_url}")
        
    elif choice == "2":
        print("\n📊 Status check complete!")
        
    elif choice == "3":
        show_setup_instructions()
    
    else:
        print("❌ Invalid choice!")

def show_setup_instructions():
    """Show detailed setup instructions."""
    instructions = """
📱 WhatsApp Business API Setup Instructions

1. 🏢 CREATE FACEBOOK APP:
   - Go to https://developers.facebook.com/apps
   - Create a new app or use existing one
   - Add WhatsApp Business product

2. 🔑 GET CREDENTIALS:
   - Note your App ID and App Secret
   - Get a temporary access token (24 hours)
   - Get a permanent access token for production

3. 📱 CONFIGURE PHONE NUMBER:
   - Add a phone number to your WhatsApp Business account
   - Verify the phone number
   - Note the Phone Number ID

4. 🔗 SET UP WEBHOOK:
   - In WhatsApp > Configuration
   - Set Callback URL: https://jarvis-bot-ftpp.onrender.com/webhook/whatsapp
   - Set Verify Token: jarvis_webhook_2024
   - Subscribe to: messages, message_deliveries, message_reads

5. 🧪 TEST YOUR BOT:
   - Send a message to your WhatsApp Business number
   - The bot should respond automatically

6. 📋 REQUIRED .ENV VARIABLES:
   WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
   WHATSAPP_WEBHOOK_VERIFY_TOKEN=jarvis_webhook_2024

🔗 Helpful Links:
- WhatsApp Business API Docs: https://developers.facebook.com/docs/whatsapp
- Getting Started: https://developers.facebook.com/docs/whatsapp/getting-started
    """
    print(instructions)

if __name__ == "__main__":
    main()
