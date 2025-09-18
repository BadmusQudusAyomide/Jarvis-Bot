#!/usr/bin/env python3
"""
WhatsApp Bot Issue Fix Script

This script fixes the specific issues identified in the WhatsApp bot:
1. /emails command failures
2. Tech quote inconsistencies  
3. Facebook download issues
4. Generic error handling
"""

import os
import sys
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppFixer:
    """Fix WhatsApp bot issues."""
    
    def __init__(self):
        self.fixes_applied = []
        
    def fix_email_command_handling(self):
        """Fix the /emails command to handle missing configuration gracefully."""
        logger.info("🔧 Fixing /emails command handling...")
        
        try:
            # Read the current WhatsApp integration
            whatsapp_file = os.path.join(project_root, 'integrations', 'whatsapp.py')
            
            with open(whatsapp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if the fix is already applied
            if 'email_summary_safe' in content:
                logger.info("✅ Email command fix already applied")
                return True
            
            # Add improved email command handling
            email_fix = '''
            elif command.startswith('/email_summary') or command == '/emails':
                try:
                    # Safe email handling with better error messages
                    count = 5
                    parts = command.split()
                    if len(parts) > 1:
                        try:
                            count = max(1, min(20, int(parts[1])))
                        except Exception:
                            pass
                    
                    # Check if email is configured before attempting
                    if not hasattr(self, 'email_agent') or self.email_agent is None:
                        self.email_agent = EmailAgent()
                    
                    # Validate email configuration
                    if not all([self.email_agent.host, self.email_agent.username, self.email_agent.password]):
                        config_help = """📧 **Email Not Configured**

To enable email checking, add these to your .env file:

```
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_SSL=true
```

For Gmail, use an App Password instead of your regular password.
Get it at: https://myaccount.google.com/apppasswords"""
                        self.send_text_message(sender, config_help)
                        return
                    
                    self.send_text_message(sender, "📬 Fetching recent emails...")
                    
                    # Attempt to fetch emails with timeout
                    try:
                        emails = self.email_agent.fetch_recent_emails(limit=count)
                        if not emails:
                            self.send_text_message(sender, "📧 No recent emails found.")
                            return
                        
                        summary = self.email_agent.summarize_emails(emails)
                        self.send_text_message(sender, f"📧 **Email Summary:**\\n\\n{summary}")
                        
                    except Exception as fetch_error:
                        error_msg = str(fetch_error)
                        if "authentication" in error_msg.lower():
                            self.send_text_message(sender, "❌ Email authentication failed. Check your IMAP credentials.")
                        elif "connection" in error_msg.lower():
                            self.send_text_message(sender, "❌ Could not connect to email server. Check your network.")
                        else:
                            self.send_text_message(sender, f"❌ Email error: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"/emails command error: {e}")
                    self.send_text_message(sender, "❌ I couldn't check your emails right now. Please try again later.")'''
            
            # Replace the existing email command handling
            old_pattern = '''elif command.startswith('/email_summary'):
                try:
                    count = 5
                    parts = command.split()
                    if len(parts) > 1:
                        try:
                            count = max(1, min(20, int(parts[1])))
                        except Exception:
                            pass
                    if not hasattr(self, 'email_agent') or self.email_agent is None:
                        self.email_agent = EmailAgent()
                    self.send_text_message(sender, "📬 Fetching recent emails...")
                    emails = self.email_agent.fetch_recent_emails(limit=count)
                    summary = self.email_agent.summarize_emails(emails)
                    self.send_text_message(sender, summary)
                except Exception as e:
                    logger.error(f"/email_summary error: {e}")
                    self.send_text_message(sender, "I couldn't summarize your inbox. Check IMAP settings.")'''
            
            if old_pattern in content:
                content = content.replace(old_pattern, email_fix)
                
                with open(whatsapp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Fixed /emails command handling")
                self.fixes_applied.append("Email command handling")
                return True
            else:
                logger.warning("⚠️ Could not find email command pattern to replace")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fix email command: {e}")
            return False
    
    def fix_tech_quote_error_handling(self):
        """Fix tech quote command to provide better error messages."""
        logger.info("🔧 Fixing tech quote error handling...")
        
        try:
            # Read the social media manager
            social_file = os.path.join(project_root, 'core', 'social_media_manager.py')
            
            with open(social_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if fix is already applied
            if 'tech_quote_safe_posting' in content:
                logger.info("✅ Tech quote fix already applied")
                return True
            
            # Find and improve the tech quote handling
            old_tech_quote = '''elif 'tech quote' in message_lower:
                quote = random.choice(self.tech_quotes)
                content = f"💡 {quote}\\n\\n#TechQuotes #Inspiration"
                result = self.post_to_both_platforms(content, user_id)
                
                if result['success']:
                    return f"✅ Posted tech quote to {', '.join(result['posted_to'])}!"
                else:
                    return "❌ Failed to post tech quote."'''
            
            new_tech_quote = '''elif 'tech quote' in message_lower:
                # tech_quote_safe_posting - marker for fix detection
                try:
                    quote = random.choice(self.tech_quotes)
                    content = f"💡 {quote}\\n\\n#TechQuotes #Inspiration"
                    
                    # Check if APIs are configured
                    if not self.twitter_api and not self.facebook_api:
                        return "❌ Social media APIs not configured. Use /setupsocial for instructions."
                    
                    result = self.post_to_both_platforms(content, user_id)
                    
                    if result['success']:
                        platforms = ', '.join(result['posted_to'])
                        return f"✅ Posted tech quote to {platforms}!"
                    else:
                        error_details = result.get('errors', {})
                        if error_details:
                            error_msg = "❌ Failed to post tech quote:\\n"
                            for platform, error in error_details.items():
                                error_msg += f"• {platform}: {error}\\n"
                            return error_msg
                        else:
                            return "❌ Failed to post tech quote. Check your API credentials."
                            
                except Exception as e:
                    logger.error(f"Tech quote error: {e}")
                    return f"❌ Tech quote error: {str(e)}"'''
            
            if old_tech_quote in content:
                content = content.replace(old_tech_quote, new_tech_quote)
                
                with open(social_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Fixed tech quote error handling")
                self.fixes_applied.append("Tech quote error handling")
                return True
            else:
                logger.warning("⚠️ Could not find tech quote pattern to replace")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fix tech quote handling: {e}")
            return False
    
    def fix_facebook_download_handling(self):
        """Fix Facebook download to handle new URL formats."""
        logger.info("🔧 Fixing Facebook download handling...")
        
        try:
            # Read the WhatsApp integration
            whatsapp_file = os.path.join(project_root, 'integrations', 'whatsapp.py')
            
            with open(whatsapp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if fix is already applied
            if 'facebook_download_improved' in content:
                logger.info("✅ Facebook download fix already applied")
                return True
            
            # Add improved Facebook handling
            facebook_fix = '''
            # Facebook links (improved handling)
            # facebook_download_improved - marker for fix detection
            facebook_patterns = [r'facebook\\.com', r'fb\\.watch', r'm\\.facebook\\.com']
            if any(re.search(pattern, message_text, re.IGNORECASE) for pattern in facebook_patterns):
                self.send_text_message(sender, "⬇️ Attempting to download Facebook video...")
                url_match = re.search(r'https?://\\S+', message_text)
                if not url_match:
                    self.send_text_message(sender, "I couldn't find a valid Facebook URL in your message.")
                    return
                url = url_match.group(0)
                logger.info(f"Detected Facebook URL from WhatsApp: {url}")
                
                try:
                    from core.youtube_utils import YouTubeDownloader
                    downloader = YouTubeDownloader()
                    file_path, error = downloader.download_video(url, quality='240p')
                    
                    if file_path:
                        try:
                            sent_ok = self._send_video_file(sender, file_path)
                            if not sent_ok:
                                self.send_text_message(sender, "Downloaded the video but couldn't send it. It may be too large for WhatsApp.")
                        finally:
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception as cleanup_err:
                                logger.warning(f"Cleanup failed for {file_path}: {cleanup_err}")
                    else:
                        # Provide more helpful error message
                        if "private" in str(error).lower():
                            self.send_text_message(sender, "❌ This Facebook video is private or restricted.")
                        elif "not found" in str(error).lower():
                            self.send_text_message(sender, "❌ Facebook video not found. The link may be expired.")
                        else:
                            self.send_text_message(sender, f"❌ Failed to download Facebook video: {error}")
                            
                except Exception as fb_error:
                    logger.error(f"Facebook download error: {fb_error}")
                    self.send_text_message(sender, "❌ Facebook downloads are currently having issues. Try again later.")
                return'''
            
            # Find the existing Facebook handling and replace it
            old_facebook_pattern = '''# Instagram/TikTok links
            ig_tt_patterns = [r'instagram\\.com', r'instagr\\.am', r'tiktok\\.com', r'vm\\.tiktok\\.com']'''
            
            if old_facebook_pattern in content:
                # Insert the Facebook fix before Instagram/TikTok
                content = content.replace(old_facebook_pattern, facebook_fix + '\n            ' + old_facebook_pattern)
                
                with open(whatsapp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Fixed Facebook download handling")
                self.fixes_applied.append("Facebook download handling")
                return True
            else:
                logger.warning("⚠️ Could not find Facebook download pattern to replace")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fix Facebook download: {e}")
            return False
    
    def fix_generic_error_responses(self):
        """Fix generic error responses to be more specific."""
        logger.info("🔧 Fixing generic error responses...")
        
        try:
            # Read the WhatsApp integration
            whatsapp_file = os.path.join(project_root, 'integrations', 'whatsapp.py')
            
            with open(whatsapp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if fix is already applied
            if 'improved_error_handling' in content:
                logger.info("✅ Generic error fix already applied")
                return True
            
            # Replace generic error messages
            old_generic = '''except Exception as e:
            logger.error(f"Error handling WhatsApp text message: {e}")
            self.send_text_message(sender, "Sorry, I encountered an error processing your message.")'''
            
            new_specific = '''except Exception as e:
            # improved_error_handling - marker for fix detection
            logger.error(f"Error handling WhatsApp text message: {e}")
            
            # Provide more specific error messages
            error_str = str(e).lower()
            if "api" in error_str:
                self.send_text_message(sender, "❌ API service temporarily unavailable. Please try again in a moment.")
            elif "network" in error_str or "connection" in error_str:
                self.send_text_message(sender, "❌ Network connection issue. Please check your internet and try again.")
            elif "authentication" in error_str or "unauthorized" in error_str:
                self.send_text_message(sender, "❌ Authentication error. Please contact support.")
            elif "timeout" in error_str:
                self.send_text_message(sender, "❌ Request timed out. Please try again.")
            else:
                self.send_text_message(sender, f"❌ I encountered an error: {str(e)[:100]}... Please try again or contact support.")'''
            
            if old_generic in content:
                content = content.replace(old_generic, new_specific)
                
                with open(whatsapp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Fixed generic error responses")
                self.fixes_applied.append("Generic error responses")
                return True
            else:
                logger.warning("⚠️ Could not find generic error pattern to replace")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fix generic errors: {e}")
            return False
    
    def create_env_template(self):
        """Create a comprehensive .env template with all required settings."""
        logger.info("🔧 Creating comprehensive .env template...")
        
        try:
            env_template = '''# Jarvis Bot Configuration
# Copy this to .env and fill in your actual values

# Core AI
GEMINI_API_KEY=your_gemini_api_key_here

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=jarvis_webhook_2024

# Email Configuration (for /emails command)
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_SSL=true

# Twitter/X API (for social media posting)
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Facebook API (for social media posting)
FACEBOOK_PAGE_ACCESS_TOKEN=your_facebook_page_token
FACEBOOK_PAGE_ID=your_facebook_page_id
FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_app_secret

# Optional: Public URL for media serving
PUBLIC_BASE_URL=https://your-app.onrender.com

# Memory Optimization (for Render deployment)
DISABLE_EMBEDDINGS=true
DISABLE_WHISPER=true
DISABLE_SPEECH=true
DISABLE_VOICE=true

# Email Digest (optional)
WHATSAPP_DIGEST_TO=your_whatsapp_number_for_digests
'''
            
            template_file = os.path.join(project_root, '.env.template')
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(env_template)
            
            logger.info("✅ Created .env.template file")
            self.fixes_applied.append("Environment template")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create .env template: {e}")
            return False
    
    def run_all_fixes(self):
        """Run all fixes."""
        logger.info("🚀 Starting WhatsApp Bot Issue Fixes")
        logger.info(f"Timestamp: {datetime.now()}")
        
        fixes = [
            ("Email Command Handling", self.fix_email_command_handling),
            ("Tech Quote Error Handling", self.fix_tech_quote_error_handling),
            ("Facebook Download Handling", self.fix_facebook_download_handling),
            ("Generic Error Responses", self.fix_generic_error_responses),
            ("Environment Template", self.create_env_template)
        ]
        
        success_count = 0
        
        for fix_name, fix_func in fixes:
            logger.info(f"\n{'='*50}")
            logger.info(f"Applying: {fix_name}")
            logger.info(f"{'='*50}")
            
            try:
                if fix_func():
                    success_count += 1
                    logger.info(f"✅ {fix_name}: SUCCESS")
                else:
                    logger.error(f"❌ {fix_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {fix_name}: EXCEPTION - {e}")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("🏁 FIX SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Applied: {success_count}/{len(fixes)} fixes")
        logger.info(f"Success Rate: {(success_count/len(fixes))*100:.1f}%")
        
        if self.fixes_applied:
            logger.info(f"\n✅ FIXES APPLIED:")
            for fix in self.fixes_applied:
                logger.info(f"  • {fix}")
        
        logger.info(f"\n📋 NEXT STEPS:")
        logger.info("1. Review and update your .env file using .env.template")
        logger.info("2. Test the bot with: python tests/command_test.py")
        logger.info("3. Deploy the updated bot to Render")
        logger.info("4. Test the failing commands in WhatsApp")
        
        return success_count == len(fixes)

def main():
    """Main function."""
    fixer = WhatsAppFixer()
    fixer.run_all_fixes()

if __name__ == "__main__":
    main()
