#!/usr/bin/env python3
"""
Fix Gemini API Quota Issues

This script addresses the main issue: Gemini API quota exhaustion
causing generic error messages in WhatsApp.
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuotaFixer:
    """Fix quota-related issues."""
    
    def fix_gemini_quota_handling(self):
        """Add better quota handling to the AI engine."""
        logger.info("🔧 Adding Gemini quota handling...")
        
        try:
            ai_engine_file = os.path.join(project_root, 'core', 'ai_engine.py')
            
            with open(ai_engine_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if fix is already applied
            if 'quota_exceeded_handler' in content:
                logger.info("✅ Quota handling already applied")
                return True
            
            # Find the generate_response method and add quota handling
            old_generate = '''def generate_response(self, message: str, context: Dict = None) -> str:
        """
        Generate AI response using the configured model.
        
        Args:
            message (str): User message
            context (Dict): Optional context information
            
        Returns:
            str: AI generated response
        """
        try:
            # Build context-aware prompt
            prompt = self._build_prompt(message, context or {})
            
            if self.provider == 'gemini':
                response = self.gemini_model.generate_content(prompt)
                return response.text if response else "I couldn't generate a response."
            
            return "AI service temporarily unavailable."
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I encountered an error while processing your request."'''
            
            new_generate = '''def generate_response(self, message: str, context: Dict = None) -> str:
        """
        Generate AI response using the configured model.
        
        Args:
            message (str): User message
            context (Dict): Optional context information
            
        Returns:
            str: AI generated response
        """
        try:
            # Build context-aware prompt
            prompt = self._build_prompt(message, context or {})
            
            if self.provider == 'gemini':
                response = self.gemini_model.generate_content(prompt)
                return response.text if response else "I couldn't generate a response."
            
            return "AI service temporarily unavailable."
            
        except Exception as e:
            # quota_exceeded_handler - marker for fix detection
            error_str = str(e).lower()
            logger.error(f"Error generating AI response: {e}")
            
            # Handle specific quota errors
            if "quota" in error_str or "429" in error_str:
                return """🚫 **AI Quota Exceeded**
                
I've reached my daily AI processing limit. Here's what you can still do:

✅ **Working Commands:**
• Social media: "tech quote", "post to twitter: message"
• Downloads: Send YouTube, TikTok, Instagram links
• Basic commands: /help, /status, /reminders

🔄 **AI will reset in a few hours**
Try AI-powered features like conversations and email summaries later.

💡 **Tip:** Use specific commands above for immediate help!"""
            
            elif "authentication" in error_str or "unauthorized" in error_str:
                return "🔑 AI authentication issue. Please contact support."
            
            elif "network" in error_str or "connection" in error_str:
                return "🌐 Network issue. Please try again in a moment."
            
            else:
                return f"⚠️ AI processing error. Try using specific commands like 'tech quote' or /help instead."'''
            
            if old_generate in content:
                content = content.replace(old_generate, new_generate)
                
                with open(ai_engine_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Added Gemini quota handling")
                return True
            else:
                logger.warning("⚠️ Could not find generate_response method to update")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fix quota handling: {e}")
            return False
    
    def add_fallback_responses(self):
        """Add fallback responses for when AI is unavailable."""
        logger.info("🔧 Adding fallback responses...")
        
        try:
            assistant_file = os.path.join(project_root, 'core', 'assistant.py')
            
            with open(assistant_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if fix is already applied
            if 'fallback_responses_added' in content:
                logger.info("✅ Fallback responses already added")
                return True
            
            # Add fallback response method
            fallback_method = '''
    def get_fallback_response(self, message: str) -> str:
        """
        Get fallback response when AI is unavailable.
        # fallback_responses_added - marker for fix detection
        """
        message_lower = message.lower().strip()
        
        # Handle common queries without AI
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "👋 Hello! I'm having some AI processing issues right now, but I can still help with:\\n\\n• Social media: 'tech quote'\\n• Downloads: Send YouTube/TikTok links\\n• Commands: /help, /status"
        
        elif any(word in message_lower for word in ['weather']):
            return "🌤️ Weather service temporarily unavailable. Try again later or use /help for other features."
        
        elif any(word in message_lower for word in ['news']):
            return "📰 News service temporarily unavailable. Try again later or use /help for other features."
        
        elif 'tech quote' in message_lower:
            # This should be handled by social media manager
            return "💡 Use the exact phrase 'tech quote' to post inspiration!"
        
        else:
            return """🤖 **AI Processing Temporarily Limited**

I can still help you with:

✅ **Social Media:**
• "tech quote" - Post inspiration
• "post to twitter: your message"

✅ **Downloads:**
• Send YouTube, TikTok, Instagram links

✅ **Commands:**
• /help - Full command list
• /status - System status
• /reminders - Your reminders

🔄 **Full AI chat will return soon!**"""
'''
            
            # Find a good place to insert the method (after __init__)
            init_end = content.find('def generate_image_file')
            if init_end != -1:
                content = content[:init_end] + fallback_method + '\n    ' + content[init_end:]
                
                with open(assistant_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Added fallback responses")
                return True
            else:
                logger.warning("⚠️ Could not find insertion point for fallback method")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to add fallback responses: {e}")
            return False
    
    def update_whatsapp_error_handling(self):
        """Update WhatsApp integration to use fallback responses."""
        logger.info("🔧 Updating WhatsApp error handling...")
        
        try:
            whatsapp_file = os.path.join(project_root, 'integrations', 'whatsapp.py')
            
            with open(whatsapp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if fix is already applied
            if 'whatsapp_fallback_updated' in content:
                logger.info("✅ WhatsApp fallback already updated")
                return True
            
            # Update the text message processing to use fallbacks
            old_processing = '''# Process with assistant
            response = self.assistant.process_text_message(message_text)
            
            # Send response
            self.send_text_message(sender, response)'''
            
            new_processing = '''# Process with assistant
            try:
                response = self.assistant.process_text_message(message_text)
                
                # Check if response indicates AI issues and use fallback
                if "I apologize, but I encountered an error" in response:
                    # whatsapp_fallback_updated - marker for fix detection
                    fallback_response = self.assistant.get_fallback_response(message_text)
                    self.send_text_message(sender, fallback_response)
                else:
                    self.send_text_message(sender, response)
                    
            except Exception as process_error:
                logger.error(f"Message processing error: {process_error}")
                fallback_response = self.assistant.get_fallback_response(message_text)
                self.send_text_message(sender, fallback_response)'''
            
            if old_processing in content:
                content = content.replace(old_processing, new_processing)
                
                with open(whatsapp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("✅ Updated WhatsApp error handling")
                return True
            else:
                logger.warning("⚠️ Could not find WhatsApp processing pattern to update")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update WhatsApp error handling: {e}")
            return False
    
    def create_quota_monitoring(self):
        """Create a simple quota monitoring script."""
        logger.info("🔧 Creating quota monitoring...")
        
        try:
            monitor_script = '''#!/usr/bin/env python3
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
'''
            
            monitor_file = os.path.join(project_root, 'check_quota.py')
            with open(monitor_file, 'w', encoding='utf-8') as f:
                f.write(monitor_script)
            
            logger.info("✅ Created quota monitoring script")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create quota monitor: {e}")
            return False
    
    def run_all_fixes(self):
        """Run all quota-related fixes."""
        logger.info("🚀 Starting Quota Issue Fixes")
        
        fixes = [
            ("Gemini Quota Handling", self.fix_gemini_quota_handling),
            ("Fallback Responses", self.add_fallback_responses),
            ("WhatsApp Error Handling", self.update_whatsapp_error_handling),
            ("Quota Monitoring", self.create_quota_monitoring)
        ]
        
        success_count = 0
        
        for fix_name, fix_func in fixes:
            logger.info(f"\n{'='*50}")
            logger.info(f"Applying: {fix_name}")
            logger.info(f"{'='*50}")
            
            if fix_func():
                success_count += 1
                logger.info(f"✅ {fix_name}: SUCCESS")
            else:
                logger.error(f"❌ {fix_name}: FAILED")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("🏁 QUOTA FIX SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Applied: {success_count}/{len(fixes)} fixes")
        
        logger.info(f"\n📋 NEXT STEPS:")
        logger.info("1. Run: python check_quota.py")
        logger.info("2. Wait for Gemini quota reset (if needed)")
        logger.info("3. Consider upgrading Gemini API plan")
        logger.info("4. Test bot with improved error messages")
        logger.info("5. Deploy updated bot to Render")
        
        return success_count == len(fixes)

def main():
    """Main function."""
    fixer = QuotaFixer()
    fixer.run_all_fixes()

if __name__ == "__main__":
    main()
