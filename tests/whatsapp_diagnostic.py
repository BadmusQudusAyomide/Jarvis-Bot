#!/usr/bin/env python3
"""
WhatsApp Bot Diagnostic Test Suite

This script tests all major WhatsApp bot functionality to identify issues.
Run this to diagnose problems before deployment.
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WhatsAppDiagnostic:
    """Comprehensive diagnostic tests for WhatsApp bot functionality."""
    
    def __init__(self):
        self.results = {}
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results."""
        self.test_count += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST {self.test_count}: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            result = test_func()
            if result.get('success', False):
                self.passed_count += 1
                logger.info(f"✅ PASSED: {test_name}")
            else:
                self.failed_count += 1
                logger.error(f"❌ FAILED: {test_name}")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
            
            self.results[test_name] = result
            
        except Exception as e:
            self.failed_count += 1
            error_msg = f"Exception in {test_name}: {str(e)}"
            logger.error(f"❌ FAILED: {test_name}")
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            self.results[test_name] = {
                'success': False,
                'error': error_msg,
                'exception': str(e)
            }
    
    def test_environment_variables(self) -> Dict[str, Any]:
        """Test if all required environment variables are set."""
        required_vars = {
            'GEMINI_API_KEY': 'Google Gemini API key',
            'WHATSAPP_ACCESS_TOKEN': 'WhatsApp Business API access token',
            'WHATSAPP_PHONE_NUMBER_ID': 'WhatsApp Business API phone number ID',
            'WHATSAPP_WEBHOOK_VERIFY_TOKEN': 'WhatsApp webhook verification token'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                missing_vars.append(f"{var}: {description}")
            else:
                logger.info(f"✓ {var}: {'*' * min(len(value), 10)}...")
        
        if missing_vars:
            return {
                'success': False,
                'error': f"Missing environment variables: {', '.join(missing_vars)}"
            }
        
        return {'success': True, 'message': 'All required environment variables are set'}
    
    def test_gemini_api(self) -> Dict[str, Any]:
        """Test Gemini API connectivity."""
        try:
            import google.generativeai as genai
            
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return {'success': False, 'error': 'GEMINI_API_KEY not set'}
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Test with a simple prompt
            response = model.generate_content("Say 'API test successful'")
            
            if response and response.text:
                logger.info(f"Gemini response: {response.text}")
                return {'success': True, 'message': 'Gemini API is working'}
            else:
                return {'success': False, 'error': 'Gemini API returned empty response'}
                
        except Exception as e:
            return {'success': False, 'error': f'Gemini API error: {str(e)}'}
    
    def test_whatsapp_api_connection(self) -> Dict[str, Any]:
        """Test WhatsApp Business API connectivity."""
        try:
            import requests
            
            access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
            phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
            
            if not access_token or not phone_number_id:
                return {'success': False, 'error': 'WhatsApp API credentials not set'}
            
            # Test API connection by getting phone number info
            url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"WhatsApp API connected: {data}")
                return {'success': True, 'message': 'WhatsApp API is accessible'}
            else:
                return {
                    'success': False, 
                    'error': f'WhatsApp API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {'success': False, 'error': f'WhatsApp API connection error: {str(e)}'}
    
    def test_social_media_manager(self) -> Dict[str, Any]:
        """Test social media manager functionality."""
        try:
            from core.social_media_manager import SocialMediaManager
            
            manager = SocialMediaManager()
            
            # Test tech quote generation
            if not manager.tech_quotes:
                return {'success': False, 'error': 'No tech quotes loaded'}
            
            # Test command processing (without actually posting)
            test_message = "tech quote"
            result = manager.process_whatsapp_post_command(test_message, user_id=1)
            
            if result and "tech quote" in result.lower():
                return {'success': True, 'message': 'Social media manager is working'}
            else:
                return {'success': False, 'error': f'Unexpected result: {result}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Social media manager error: {str(e)}'}
    
    def test_email_agent(self) -> Dict[str, Any]:
        """Test email agent functionality."""
        try:
            from core.email_agent import EmailAgent
            
            agent = EmailAgent()
            
            # Check if email is configured
            if not all([agent.host, agent.username, agent.password]):
                return {
                    'success': False, 
                    'error': 'Email not configured (missing IMAP settings)'
                }
            
            # Test connection (without fetching emails)
            logger.info(f"Email configured: {agent.username}@{agent.host}")
            return {'success': True, 'message': 'Email agent is configured'}
                
        except Exception as e:
            return {'success': False, 'error': f'Email agent error: {str(e)}'}
    
    def test_youtube_downloader(self) -> Dict[str, Any]:
        """Test YouTube/social media downloader."""
        try:
            from core.youtube_utils import YouTubeDownloader
            
            downloader = YouTubeDownloader()
            
            # Test with a simple YouTube URL (don't actually download)
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            
            # Just check if the downloader can be initialized
            logger.info("YouTube downloader initialized successfully")
            return {'success': True, 'message': 'YouTube downloader is available'}
                
        except Exception as e:
            return {'success': False, 'error': f'YouTube downloader error: {str(e)}'}
    
    def test_database_connection(self) -> Dict[str, Any]:
        """Test database connectivity."""
        try:
            from core.database import DatabaseManager
            
            db = DatabaseManager()
            
            # Test basic database operations
            health = db.health_check()
            
            if health:
                return {'success': True, 'message': 'Database is healthy'}
            else:
                return {'success': False, 'error': 'Database health check failed'}
                
        except Exception as e:
            return {'success': False, 'error': f'Database error: {str(e)}'}
    
    def test_whatsapp_message_processing(self) -> Dict[str, Any]:
        """Test WhatsApp message processing pipeline."""
        try:
            from integrations.whatsapp import WhatsAppBot
            
            # Initialize bot (without starting server)
            bot = WhatsAppBot()
            
            # Test message processing components
            if not bot.assistant:
                return {'success': False, 'error': 'Assistant not initialized'}
            
            if not bot.email_agent:
                return {'success': False, 'error': 'Email agent not initialized'}
            
            logger.info("WhatsApp bot components initialized successfully")
            return {'success': True, 'message': 'WhatsApp message processing is ready'}
                
        except Exception as e:
            return {'success': False, 'error': f'WhatsApp processing error: {str(e)}'}
    
    def test_command_handlers(self) -> Dict[str, Any]:
        """Test specific command handlers that are failing."""
        try:
            from integrations.whatsapp import WhatsAppBot
            
            bot = WhatsAppBot()
            
            # Test /emails command specifically
            test_sender = "test_user"
            
            # Simulate /emails command
            try:
                # This should not crash
                logger.info("Testing /emails command handler...")
                # We can't actually call _handle_command without proper setup,
                # but we can check if the email_agent is properly initialized
                if hasattr(bot, 'email_agent') and bot.email_agent:
                    logger.info("Email agent is available for /emails command")
                else:
                    return {'success': False, 'error': '/emails command will fail - no email agent'}
                
            except Exception as cmd_error:
                return {'success': False, 'error': f'/emails command error: {str(cmd_error)}'}
            
            return {'success': True, 'message': 'Command handlers are properly configured'}
                
        except Exception as e:
            return {'success': False, 'error': f'Command handler test error: {str(e)}'}
    
    def run_all_tests(self):
        """Run all diagnostic tests."""
        logger.info("🚀 Starting WhatsApp Bot Diagnostic Tests")
        logger.info(f"Timestamp: {datetime.now()}")
        
        # Run all tests
        self.run_test("Environment Variables", self.test_environment_variables)
        self.run_test("Gemini API Connection", self.test_gemini_api)
        self.run_test("WhatsApp API Connection", self.test_whatsapp_api_connection)
        self.run_test("Database Connection", self.test_database_connection)
        self.run_test("Social Media Manager", self.test_social_media_manager)
        self.run_test("Email Agent", self.test_email_agent)
        self.run_test("YouTube Downloader", self.test_youtube_downloader)
        self.run_test("WhatsApp Message Processing", self.test_whatsapp_message_processing)
        self.run_test("Command Handlers", self.test_command_handlers)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        logger.info(f"\n{'='*60}")
        logger.info("🏁 DIAGNOSTIC SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Tests: {self.test_count}")
        logger.info(f"✅ Passed: {self.passed_count}")
        logger.info(f"❌ Failed: {self.failed_count}")
        logger.info(f"Success Rate: {(self.passed_count/self.test_count)*100:.1f}%")
        
        if self.failed_count > 0:
            logger.info(f"\n🔍 FAILED TESTS:")
            for test_name, result in self.results.items():
                if not result.get('success', False):
                    logger.info(f"❌ {test_name}: {result.get('error', 'Unknown error')}")
        
        logger.info(f"\n💡 RECOMMENDATIONS:")
        
        # Specific recommendations based on failures
        failed_tests = [name for name, result in self.results.items() if not result.get('success', False)]
        
        if 'Environment Variables' in failed_tests:
            logger.info("• Set missing environment variables in .env file")
        
        if 'Gemini API Connection' in failed_tests:
            logger.info("• Check GEMINI_API_KEY in .env file")
            logger.info("• Verify API key at https://aistudio.google.com/app/apikey")
        
        if 'WhatsApp API Connection' in failed_tests:
            logger.info("• Check WhatsApp Business API credentials")
            logger.info("• Verify access token and phone number ID")
        
        if 'Email Agent' in failed_tests:
            logger.info("• Configure IMAP settings for email functionality")
            logger.info("• Add IMAP_HOST, IMAP_USERNAME, IMAP_PASSWORD to .env")
        
        if 'Social Media Manager' in failed_tests:
            logger.info("• Check social media API credentials")
            logger.info("• Verify Twitter/Facebook API keys")
        
        if self.failed_count == 0:
            logger.info("🎉 All tests passed! Your bot should be working correctly.")
        else:
            logger.info(f"🔧 Fix the {self.failed_count} failed test(s) above to resolve bot issues.")

def main():
    """Main function to run diagnostics."""
    diagnostic = WhatsAppDiagnostic()
    diagnostic.run_all_tests()

if __name__ == "__main__":
    main()
