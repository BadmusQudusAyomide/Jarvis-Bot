#!/usr/bin/env python3
"""
Telegram Webhook Setup Script

This script sets up the Telegram webhook to point to your deployed application.
Run this after deploying to configure the bot to receive messages.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_telegram_webhook():
    """Set up Telegram webhook."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = "https://jarvis-bot-ftpp.onrender.com/webhook/telegram"
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return False
    
    # Set webhook
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    payload = {
        "url": webhook_url,
        "max_connections": 40,
        "allowed_updates": ["message", "edited_message", "callback_query"]
    }
    
    print(f"🔗 Setting webhook to: {webhook_url}")
    
    try:
        response = requests.post(api_url, json=payload)
        result = response.json()
        
        if result.get('ok'):
            print("✅ Webhook set successfully!")
            print(f"📋 Response: {result.get('description', 'Success')}")
            return True
        else:
            print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

def get_webhook_info():
    """Get current webhook information."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return
    
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(api_url)
        result = response.json()
        
        if result.get('ok'):
            webhook_info = result.get('result', {})
            print("\n📊 Current Webhook Info:")
            print(f"🔗 URL: {webhook_info.get('url', 'Not set')}")
            print(f"📈 Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"🕒 Last error date: {webhook_info.get('last_error_date', 'None')}")
            print(f"❌ Last error message: {webhook_info.get('last_error_message', 'None')}")
            print(f"🔄 Max connections: {webhook_info.get('max_connections', 'Default')}")
            print(f"📝 Allowed updates: {webhook_info.get('allowed_updates', 'All')}")
        else:
            print(f"❌ Failed to get webhook info: {result.get('description')}")
            
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")

def delete_webhook():
    """Delete the current webhook."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(api_url)
        result = response.json()
        
        if result.get('ok'):
            print("✅ Webhook deleted successfully!")
            return True
        else:
            print(f"❌ Failed to delete webhook: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False

def test_bot():
    """Test if the bot is responding."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        response = requests.get(api_url)
        result = response.json()
        
        if result.get('ok'):
            bot_info = result.get('result', {})
            print(f"✅ Bot is active: @{bot_info.get('username')}")
            print(f"📝 Bot name: {bot_info.get('first_name')}")
            print(f"🆔 Bot ID: {bot_info.get('id')}")
            return True
        else:
            print(f"❌ Bot test failed: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing bot: {e}")
        return False

def main():
    """Main function."""
    print("🤖 Jarvis Bot Webhook Setup")
    print("=" * 40)
    
    # Test bot first
    print("\n1️⃣ Testing bot connection...")
    if not test_bot():
        return
    
    # Get current webhook info
    print("\n2️⃣ Getting current webhook info...")
    get_webhook_info()
    
    # Ask user what to do
    print("\n3️⃣ What would you like to do?")
    print("1. Set up webhook")
    print("2. Delete webhook")
    print("3. Just check status")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        print("\n🔧 Setting up webhook...")
        if setup_telegram_webhook():
            print("\n✅ Webhook setup complete!")
            print("\n📱 Your bot should now respond to messages!")
            print("🧪 Test by sending a message to your bot on Telegram.")
        else:
            print("\n❌ Webhook setup failed!")
    
    elif choice == "2":
        print("\n🗑️ Deleting webhook...")
        if delete_webhook():
            print("\n✅ Webhook deleted!")
            print("⚠️ Your bot will no longer receive messages until webhook is set again.")
    
    elif choice == "3":
        print("\n📊 Status check complete!")
    
    else:
        print("❌ Invalid choice!")

if __name__ == "__main__":
    main()
