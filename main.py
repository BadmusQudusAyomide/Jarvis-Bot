#!/usr/bin/env python3
"""
Jarvis Bot - Main Entry Point

This is the main script that runs the Jarvis AI Assistant bot.
It handles initialization, configuration, and starts the appropriate bot integration.

Usage:
    python main.py --platform telegram    # Run Telegram bot (default)
    python main.py --platform whatsapp    # Run WhatsApp bot (when implemented)
    python main.py --help                 # Show help information
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from integrations.telegram_bot import TelegramBot
from integrations.whatsapp import WhatsAppBot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jarvis_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_environment() -> bool:
    """
    Check if all required environment variables are set.
    
    Returns:
        bool: True if environment is properly configured
    """
    required_vars = {
        'GEMINI_API_KEY': 'Google Gemini API key for AI functionality',
        'TELEGRAM_BOT_TOKEN': 'Telegram bot token (required for Telegram integration)',
        'WHATSAPP_ACCESS_TOKEN': 'WhatsApp Business API access token (required for WhatsApp integration)',
        'WHATSAPP_PHONE_NUMBER_ID': 'WhatsApp Business API phone number ID',
        'WHATSAPP_WEBHOOK_VERIFY_TOKEN': 'WhatsApp webhook verification token'
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var}: {description}")
    
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(var)
        logger.error("\nPlease set these variables in your .env file")
        return False
    
    return True

def validate_api_keys() -> bool:
    """
    Validate that API keys are working.
    
    Returns:
        bool: True if API keys are valid
    """
    try:
        # Test Gemini API key
        import google.generativeai as genai
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Make a simple test request
        response = model.generate_content("Hello")
        
        logger.info("✓ Gemini API key is valid")
        return True
        
    except Exception as e:
        logger.error(f"✗ Gemini API key validation failed: {e}")
        return False

def run_telegram_bot():
    """
    Initialize and run the Telegram bot.
    """
    try:
        logger.info("Starting Jarvis Telegram Bot...")
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user")
    except Exception as e:
        logger.error(f"Error running Telegram bot: {e}")
        sys.exit(1)

def run_whatsapp_bot():
    """
    Initialize and run the WhatsApp bot.
    """
    try:
        logger.info("Starting Jarvis WhatsApp Bot...")
        logger.warning("WhatsApp integration is not yet fully implemented")
        bot = WhatsAppBot()
        bot.run_webhook_server()
    except KeyboardInterrupt:
        logger.info("WhatsApp bot stopped by user")
    except Exception as e:
        logger.error(f"Error running WhatsApp bot: {e}")
        sys.exit(1)

def show_setup_instructions():
    """
    Show setup instructions for the bot.
    """
    instructions = """
🤖 Jarvis Bot Setup Instructions

1. INSTALL DEPENDENCIES:
   pip install -r requirements.txt

2. CONFIGURE API KEYS:
   Edit the .env file and add your API keys:
   - GEMINI_API_KEY: Get from https://aistudio.google.com/app/apikey
   - TELEGRAM_BOT_TOKEN: Get from @BotFather on Telegram

3. CREATE TELEGRAM BOT:
   - Message @BotFather on Telegram
   - Use /newbot command
   - Choose a name and username for your bot
   - Copy the token to your .env file

4. RUN THE BOT:
   python main.py --platform telegram

5. TEST THE BOT:
   - Find your bot on Telegram
   - Send /start to begin
   - Try sending text messages and voice notes

For WhatsApp integration, additional setup is required.
See integrations/whatsapp.py for more information.

Need help? Check the README.md file or the documentation.
    """
    print(instructions)

def main():
    """
    Main function - parse arguments and run the appropriate bot.
    """
    parser = argparse.ArgumentParser(
        description='Jarvis AI Assistant Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Run Telegram bot (default)
  python main.py --platform telegram   # Run Telegram bot explicitly
  python main.py --platform whatsapp   # Run WhatsApp bot
  python main.py --setup               # Show setup instructions
  python main.py --check-env           # Check environment configuration
        """
    )
    
    parser.add_argument(
        '--platform',
        choices=['telegram', 'whatsapp'],
        default='telegram',
        help='Platform to run the bot on (default: telegram)'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Show setup instructions'
    )
    
    parser.add_argument(
        '--check-env',
        action='store_true',
        help='Check environment configuration'
    )
    
    parser.add_argument(
        '--validate-keys',
        action='store_true',
        help='Validate API keys'
    )
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.setup:
        show_setup_instructions()
        return
    
    if args.check_env:
        if check_environment():
            logger.info("✓ Environment configuration is valid")
        else:
            sys.exit(1)
        return
    
    if args.validate_keys:
        if validate_api_keys():
            logger.info("✓ API keys are valid")
        else:
            sys.exit(1)
        return
    
    # Check environment before starting
    if not check_environment():
        logger.error("Environment check failed. Use --setup for instructions.")
        sys.exit(1)
    
    # Start the appropriate bot
    logger.info(f"Jarvis Bot starting on platform: {args.platform}")
    
    if args.platform == 'telegram':
        run_telegram_bot()
    elif args.platform == 'whatsapp':
        run_whatsapp_bot()
    else:
        logger.error(f"Unsupported platform: {args.platform}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Jarvis Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
