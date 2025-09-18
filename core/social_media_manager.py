import os
import tweepy
import facebook
import schedule
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .database import DatabaseManager
from .ai_engine import AIEngine

logger = logging.getLogger(__name__)

class SocialMediaManager:
    """
    Manages social media posting for Twitter and Facebook.
    Handles scheduled posts, direct posting, and content generation.
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.ai = AIEngine()
        
        # Twitter/X API setup
        self.twitter_api = self._setup_twitter()
        
        # Facebook API setup
        self.facebook_api = self._setup_facebook()
        
        # Tech quotes database
        self.tech_quotes = self._load_tech_quotes()
        
    def _setup_twitter(self):
        """Setup Twitter API client."""
        try:
            api_key = os.getenv('TWITTER_API_KEY')
            api_secret = os.getenv('TWITTER_API_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            
            if not all([api_key, api_secret, access_token, access_token_secret]):
                logger.warning("Twitter API credentials not found")
                return None
                
            # Twitter API v2 client
            client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            logger.info("Twitter API initialized successfully")
            return client
            
        except Exception as e:
            logger.error(f"Failed to setup Twitter API: {e}")
            return None
    
    def _setup_facebook(self):
        """Setup Facebook API client."""
        try:
            access_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')
            
            if not access_token:
                logger.warning("Facebook API credentials not found")
                return None
                
            graph = facebook.GraphAPI(access_token=access_token, version="3.1")
            logger.info("Facebook API initialized successfully")
            return graph
            
        except Exception as e:
            logger.error(f"Failed to setup Facebook API: {e}")
            return None
    
    def _load_tech_quotes(self) -> List[str]:
        """Load tech quotes for daily posting."""
        return [
            "The best way to predict the future is to invent it. - Alan Kay",
            "Technology is best when it brings people together. - Matt Mullenweg",
            "Innovation distinguishes between a leader and a follower. - Steve Jobs",
            "The advance of technology is based on making it fit in so that you don't really even notice it. - Bill Gates",
            "Any sufficiently advanced technology is indistinguishable from magic. - Arthur C. Clarke",
            "The real problem is not whether machines think but whether men do. - B.F. Skinner",
            "Technology is nothing. What's important is that you have a faith in people. - Steve Jobs",
            "The science of today is the technology of tomorrow. - Edward Teller",
            "Programming isn't about what you know; it's about what you can figure out. - Chris Pine",
            "Code is like humor. When you have to explain it, it's bad. - Cory House",
            "First, solve the problem. Then, write the code. - John Johnson",
            "Experience is the name everyone gives to their mistakes. - Oscar Wilde",
            "In order to be irreplaceable, one must always be different. - Coco Chanel",
            "Java is to JavaScript what car is to Carpet. - Chris Heilmann",
            "Talk is cheap. Show me the code. - Linus Torvalds",
            "The only way to learn a new programming language is by writing programs in it. - Dennis Ritchie",
            "Simplicity is the ultimate sophistication. - Leonardo da Vinci",
            "Make it work, make it right, make it fast. - Kent Beck",
            "The best error message is the one that never shows up. - Thomas Fuchs",
            "Debugging is twice as hard as writing the code in the first place. - Brian Kernighan"
        ]
    
    def post_to_twitter(self, content: str, user_id: int = None) -> Dict:
        """Post content to Twitter."""
        try:
            if not self.twitter_api:
                return {'success': False, 'error': 'Twitter API not configured'}
            
            # Check content length (Twitter limit: 280 characters)
            if len(content) > 280:
                content = content[:277] + "..."
            
            # Post tweet
            response = self.twitter_api.create_tweet(text=content)
            
            # Log to database
            if user_id:
                self._log_social_post(user_id, 'twitter', content, response.data['id'])
            
            return {
                'success': True,
                'platform': 'twitter',
                'post_id': response.data['id'],
                'content': content,
                'url': f"https://twitter.com/user/status/{response.data['id']}"
            }
            
        except Exception as e:
            logger.error(f"Failed to post to Twitter: {e}", exc_info=True)
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = "Twitter API authentication failed. Please check your API keys."
            elif "403" in error_msg or "Forbidden" in error_msg:
                error_msg = "Twitter API access denied. Check your app permissions."
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                error_msg = "Twitter API rate limit exceeded. Please try again later."
            return {'success': False, 'error': error_msg}
    
    def post_to_facebook(self, content: str, user_id: int = None) -> Dict:
        """Post content to Facebook."""
        try:
            if not self.facebook_api:
                return {'success': False, 'error': 'Facebook API not configured'}
            
            page_id = os.getenv('FACEBOOK_PAGE_ID')
            if not page_id:
                return {'success': False, 'error': 'Facebook Page ID not configured'}
            
            # Post to Facebook page
            response = self.facebook_api.put_object(
                parent_object=page_id,
                connection_name='feed',
                message=content
            )
            
            # Log to database
            if user_id:
                self._log_social_post(user_id, 'facebook', content, response['id'])
            
            return {
                'success': True,
                'platform': 'facebook',
                'post_id': response['id'],
                'content': content,
                'url': f"https://facebook.com/{response['id']}"
            }
            
        except Exception as e:
            logger.error(f"Failed to post to Facebook: {e}")
            return {'success': False, 'error': str(e)}
    
    def post_to_both_platforms(self, content: str, user_id: int = None) -> Dict:
        """Post content to both Twitter and Facebook."""
        results = {
            'twitter': self.post_to_twitter(content, user_id),
            'facebook': self.post_to_facebook(content, user_id)
        }
        
        success_count = sum(1 for result in results.values() if result['success'])
        
        return {
            'success': success_count > 0,
            'results': results,
            'posted_to': [platform for platform, result in results.items() if result['success']]
        }
    
    def schedule_daily_tech_quotes(self, user_id: int):
        """Schedule daily tech quotes at 9 AM and 6 PM."""
        def post_morning_quote():
            quote = random.choice(self.tech_quotes)
            morning_content = f"🌅 Good morning! Here's your daily tech inspiration:\n\n{quote}\n\n#TechQuotes #MorningMotivation #Technology"
            self.post_to_both_platforms(morning_content, user_id)
            logger.info("Posted morning tech quote")
        
        def post_evening_quote():
            quote = random.choice(self.tech_quotes)
            evening_content = f"🌆 Evening tech wisdom:\n\n{quote}\n\n#TechQuotes #EveningInspiration #Innovation"
            self.post_to_both_platforms(evening_content, user_id)
            logger.info("Posted evening tech quote")
        
        # Schedule daily posts
        schedule.every().day.at("09:00").do(post_morning_quote)
        schedule.every().day.at("18:00").do(post_evening_quote)
        
        logger.info("Daily tech quotes scheduled for 9 AM and 6 PM")
    
    def process_whatsapp_post_command(self, message: str, user_id: int) -> str:
        """Process WhatsApp command to post content."""
        try:
            # Parse command: "post to twitter: content" or "post to both: content"
            message_lower = message.lower().strip()
            
            if message_lower.startswith('post to twitter:'):
                content = message[16:].strip()
                result = self.post_to_twitter(content, user_id)
                
                if result['success']:
                    return f"✅ Posted to Twitter!\n🔗 {result['url']}"
                else:
                    return f"❌ Failed to post to Twitter: {result['error']}"
            
            elif message_lower.startswith('post to facebook:'):
                content = message[17:].strip()
                result = self.post_to_facebook(content, user_id)
                
                if result['success']:
                    return f"✅ Posted to Facebook!\n🔗 {result['url']}"
                else:
                    return f"❌ Failed to post to Facebook: {result['error']}"
            
            elif message_lower.startswith('post to both:'):
                content = message[13:].strip()
                result = self.post_to_both_platforms(content, user_id)
                
                if result['success']:
                    platforms = ', '.join(result['posted_to'])
                    return f"✅ Posted to {platforms}!\n\nResults:\n" + \
                           '\n'.join([f"• {platform.title()}: {'✅' if res['success'] else '❌'}" 
                                    for platform, res in result['results'].items()])
                else:
                    return "❌ Failed to post to any platform. Check your API configuration."
            
            elif 'tech quote' in message_lower:
                quote = random.choice(self.tech_quotes)
                content = f"💡 {quote}\n\n#TechQuotes #Inspiration"
                result = self.post_to_both_platforms(content, user_id)
                
                if result['success']:
                    return f"✅ Posted tech quote to {', '.join(result['posted_to'])}!"
                else:
                    return "❌ Failed to post tech quote."
            
            return None  # Not a social media command
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp post command: {e}")
            return f"❌ Error processing command: {str(e)}"
    
    def _log_social_post(self, user_id: int, platform: str, content: str, post_id: str):
        """Log social media post to database."""
        try:
            # This would save to a social_posts table
            # Implementation depends on your database schema
            logger.info(f"Logged {platform} post for user {user_id}: {post_id}")
        except Exception as e:
            logger.error(f"Failed to log social post: {e}")
    
    def get_posting_stats(self, user_id: int) -> Dict:
        """Get social media posting statistics."""
        # This would query the database for user's posting history
        return {
            'total_posts': 0,
            'twitter_posts': 0,
            'facebook_posts': 0,
            'last_post': None
        }
    
    def run_scheduler(self):
        """Run the scheduling loop."""
        logger.info("Starting social media scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
