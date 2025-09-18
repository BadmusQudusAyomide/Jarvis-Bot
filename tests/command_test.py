#!/usr/bin/env python3
"""
Command-Specific Test Suite

Tests individual WhatsApp commands that are failing in production.
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandTester:
    """Test specific commands that are failing."""
    
    def __init__(self):
        self.test_user_id = "test_user_12345"
        
    def test_tech_quote_command(self):
        """Test the 'tech quote' command specifically."""
        logger.info("🧪 Testing 'tech quote' command...")
        
        try:
            from core.social_media_manager import SocialMediaManager
            
            manager = SocialMediaManager()
            
            # Test the exact command from WhatsApp logs
            message = "tech quote"
            result = manager.process_whatsapp_post_command(message, user_id=1)
            
            logger.info(f"Tech quote result: {result}")
            
            if result and "✅" in result:
                logger.info("✅ Tech quote command working")
                return True
            elif result and "❌" in result:
                logger.error(f"❌ Tech quote command failed: {result}")
                return False
            else:
                logger.error(f"❌ Unexpected tech quote result: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Tech quote command exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_emails_command(self):
        """Test the '/emails' command specifically."""
        logger.info("🧪 Testing '/emails' command...")
        
        try:
            from core.email_agent import EmailAgent
            
            agent = EmailAgent()
            
            # Check configuration
            if not all([agent.host, agent.username, agent.password]):
                logger.warning("⚠️ Email not configured - this is why /emails fails")
                logger.info("Missing IMAP configuration:")
                logger.info(f"  IMAP_HOST: {'✓' if agent.host else '✗'}")
                logger.info(f"  IMAP_USERNAME: {'✓' if agent.username else '✗'}")
                logger.info(f"  IMAP_PASSWORD: {'✓' if agent.password else '✗'}")
                return False
            
            # Try to fetch emails (this might fail due to network/auth)
            try:
                emails = agent.fetch_recent_emails(limit=1)
                logger.info(f"✅ Email fetch successful: {len(emails)} emails")
                return True
            except Exception as fetch_error:
                logger.error(f"❌ Email fetch failed: {fetch_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Email command exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_facebook_download(self):
        """Test Facebook video download functionality."""
        logger.info("🧪 Testing Facebook video download...")
        
        try:
            from core.youtube_utils import YouTubeDownloader
            
            downloader = YouTubeDownloader()
            
            # Test with the exact URLs from WhatsApp logs
            test_urls = [
                "https://www.facebook.com/share/r/1ZWtLnR9nk/",
                "https://www.facebook.com/share/r/1CLPiMaMpx/"
            ]
            
            for url in test_urls:
                logger.info(f"Testing URL: {url}")
                
                try:
                    # Try to download (this will likely fail, but we can see why)
                    file_path, error = downloader.download_video(url, quality='240p')
                    
                    if file_path:
                        logger.info(f"✅ Download successful: {file_path}")
                        # Clean up
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return True
                    else:
                        logger.error(f"❌ Download failed: {error}")
                        
                except Exception as download_error:
                    logger.error(f"❌ Download exception: {download_error}")
            
            return False
                
        except Exception as e:
            logger.error(f"❌ Facebook download test exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_whatsapp_message_routing(self):
        """Test the message routing that's causing generic errors."""
        logger.info("🧪 Testing WhatsApp message routing...")
        
        try:
            # Test the exact flow from WhatsApp webhook to response
            from integrations.whatsapp import WhatsAppBot
            
            bot = WhatsAppBot()
            
            # Simulate the webhook data structure
            test_webhook_data = {
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": self.test_user_id,
                                "type": "text",
                                "text": {"body": "/emails"}
                            }]
                        }
                    }]
                }]
            }
            
            # This should not crash
            try:
                bot.handle_incoming_message(test_webhook_data)
                logger.info("✅ Message routing completed without crash")
                return True
            except Exception as routing_error:
                logger.error(f"❌ Message routing failed: {routing_error}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            logger.error(f"❌ Message routing test exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_assistant_processing(self):
        """Test the core assistant processing."""
        logger.info("🧪 Testing assistant message processing...")
        
        try:
            from core.assistant import JarvisAssistant
            
            assistant = JarvisAssistant()
            
            # Test basic text processing
            test_messages = [
                "Hello",
                "tech quote",
                "/help",
                "What's the weather?"
            ]
            
            for message in test_messages:
                try:
                    response = assistant.process_text_message(message)
                    logger.info(f"✅ '{message}' -> '{response[:50]}...'")
                except Exception as msg_error:
                    logger.error(f"❌ '{message}' failed: {msg_error}")
                    return False
            
            return True
                
        except Exception as e:
            logger.error(f"❌ Assistant processing test exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_command_tests(self):
        """Run all command-specific tests."""
        logger.info("🚀 Starting Command-Specific Tests")
        logger.info(f"Timestamp: {datetime.now()}")
        
        tests = [
            ("Tech Quote Command", self.test_tech_quote_command),
            ("Emails Command", self.test_emails_command),
            ("Facebook Download", self.test_facebook_download),
            ("WhatsApp Message Routing", self.test_whatsapp_message_routing),
            ("Assistant Processing", self.test_assistant_processing)
        ]
        
        results = {}
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                results[test_name] = False
                logger.error(f"❌ {test_name}: EXCEPTION - {e}")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("📊 COMMAND TEST SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Passed: {passed}/{total}")
        logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Specific recommendations
        logger.info(f"\n💡 SPECIFIC FIXES NEEDED:")
        
        if not results.get("Emails Command", False):
            logger.info("🔧 Fix /emails command:")
            logger.info("   - Add IMAP settings to .env file")
            logger.info("   - IMAP_HOST=imap.gmail.com")
            logger.info("   - IMAP_USERNAME=your-email@gmail.com")
            logger.info("   - IMAP_PASSWORD=your-app-password")
        
        if not results.get("Tech Quote Command", False):
            logger.info("🔧 Fix tech quote command:")
            logger.info("   - Check social media API credentials")
            logger.info("   - Verify Twitter/Facebook tokens in .env")
        
        if not results.get("Facebook Download", False):
            logger.info("🔧 Fix Facebook downloads:")
            logger.info("   - Facebook changed their URL structure")
            logger.info("   - May need yt-dlp update or different approach")
        
        return results

def main():
    """Main function."""
    tester = CommandTester()
    tester.run_all_command_tests()

if __name__ == "__main__":
    main()
