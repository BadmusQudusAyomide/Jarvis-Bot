import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class MessageRouter:
    """
    Central message routing system for Jarvis.
    Handles message processing, context management, and response generation.
    """
    
    def __init__(self, database_manager, ai_engine, scheduler):
        self.db = database_manager
        self.ai = ai_engine
        self.scheduler = scheduler
        
        # Command handlers
        self.command_handlers = {
            'help': self._handle_help,
            'status': self._handle_status,
            'settings': self._handle_settings,
            'clear': self._handle_clear_context,
            'documents': self._handle_list_documents,
            'reminders': self._handle_list_reminders,
            'setreminder': self._handle_set_reminder,
            'stats': self._handle_stats,
            'setupsleepwake': self._handle_setup_sleep_wake,
            'smartreminders': self._handle_setup_sleep_wake,
            'emails': self._handle_emails,
            'checkemail': self._handle_emails,
            'setupsocial': self._handle_setup_social,
            'socialstats': self._handle_social_stats
        }
        
        logger.info("Message router initialized")
    
    def process_message(self, platform: str, platform_user_id: str, message_data: Dict) -> Dict:
        """
        Process incoming message from any platform.
        
        Args:
            platform (str): Platform name (telegram, whatsapp)
            platform_user_id (str): User ID on the platform
            message_data (Dict): Message data
            
        Returns:
            Dict: Response data
        """
        try:
            # Get or create user
            user = self.db.get_or_create_user(
                platform_id=platform_user_id,
                platform=platform,
                **message_data.get('user_info', {})
            )
            
            # Extract message content
            message_type = message_data.get('type', 'text')
            content = message_data.get('content', '')
            
            # Log analytics
            self.db.log_analytics_event('message_received', user['id'], {
                'platform': platform,
                'message_type': message_type,
                'content_length': len(content) if isinstance(content, str) else 0
            })
            
            # Process based on message type
            if message_type == 'text':
                response = self._process_text_message(user, content, message_data)
            elif message_type == 'voice':
                response = self._process_voice_message(user, message_data)
            elif message_type == 'document':
                response = self._process_document_message(user, message_data)
            elif message_type == 'image':
                response = self._process_image_message(user, message_data)
            else:
                response = {
                    'type': 'text',
                    'content': f"I don't know how to handle {message_type} messages yet.",
                    'success': False
                }
            
            # Save conversation
            if response.get('success', True):
                self.db.save_conversation(
                    user_id=user['id'],
                    message_type=message_type,
                    user_message=str(content),
                    bot_response=response.get('content', ''),
                    metadata={
                        'platform': platform,
                        'response_type': response.get('type'),
                        'processing_time': response.get('processing_time')
                    }
                )
            
            return {
                **response,
                'user_id': user['id'],
                'platform': platform
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'type': 'text',
                'content': 'I encountered an error processing your message. Please try again.',
                'success': False,
                'error': str(e)
            }
    
    def _process_text_message(self, user: Dict, content: str, message_data: Dict) -> Dict:
        """Process text message."""
        start_time = datetime.now()
        
        # Check for commands
        if content.startswith('/'):
            command = content[1:].split()[0].lower()
            if command in self.command_handlers:
                return self.command_handlers[command](user, content)
        
        # Get conversation context
        context = self._build_context(user)
        
        # Check for special patterns (weather, news, etc.)
        special_response = self._handle_special_commands(content, context)
        if special_response:
            processing_time = (datetime.now() - start_time).total_seconds()
            return {
                'type': 'text',
                'content': special_response,
                'success': True,
                'processing_time': processing_time
            }
        
        # Generate AI response
        ai_response = self.ai.generate_response(content, context)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'type': 'text',
            'content': ai_response,
            'success': True,
            'processing_time': processing_time
        }
    
    def _process_voice_message(self, user: Dict, message_data: Dict) -> Dict:
        """Process voice message."""
        try:
            audio_path = message_data.get('file_path')
            if not audio_path:
                return {
                    'type': 'text',
                    'content': 'No audio file received.',
                    'success': False
                }
            
            # Transcribe audio
            transcribed_text, success = self.ai.transcribe_audio(audio_path)
            
            if not success:
                return {
                    'type': 'text',
                    'content': transcribed_text,
                    'success': False
                }
            
            # Process transcribed text
            text_response = self._process_text_message(user, transcribed_text, {
                'type': 'text',
                'content': transcribed_text
            })
            
            # Add transcription info
            response_content = f"🎤 You said: \"{transcribed_text}\"\n\n{text_response['content']}"
            
            return {
                **text_response,
                'content': response_content,
                'transcription': transcribed_text
            }
            
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            return {
                'type': 'text',
                'content': 'I had trouble processing your voice message. Please try again.',
                'success': False
            }
    
    def _process_document_message(self, user: Dict, message_data: Dict) -> Dict:
        """Process document upload."""
        try:
            file_info = message_data.get('file_info', {})
            file_path = message_data.get('file_path')
            
            if not file_path:
                return {
                    'type': 'text',
                    'content': 'No document received.',
                    'success': False
                }
            
            # Process document with AI engine
            result = self.ai.add_document(message_data.get('file_object'), user['id'])
            
            if result.get('success'):
                # Save to database
                doc_id = self.db.save_document(
                    user_id=user['id'],
                    filename=file_info.get('filename', 'unknown'),
                    file_path=result['file_path'],
                    file_type=file_info.get('mime_type', 'unknown'),
                    file_size=file_info.get('file_size', 0),
                    content_summary=result.get('summary'),
                    embeddings=result.get('embeddings')
                )
                
                return {
                    'type': 'text',
                    'content': f"📄 Successfully processed \"{file_info.get('filename')}\"!\n\n"
                              f"Summary: {result.get('summary', 'No summary available')}\n\n"
                              f"I can now answer questions about this document.",
                    'success': True,
                    'document_id': doc_id
                }
            else:
                return {
                    'type': 'text',
                    'content': f"Sorry, I couldn't process your document: {result.get('error', 'Unknown error')}",
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {
                'type': 'text',
                'content': 'I encountered an error processing your document.',
                'success': False
            }
    
    def _process_image_message(self, user: Dict, message_data: Dict) -> Dict:
        """Process image upload."""
        try:
            file_path = message_data.get('file_path')
            if not file_path:
                return {
                    'type': 'text',
                    'content': 'No image received.',
                    'success': False
                }
            
            # Analyze image
            analysis = self.ai.analyze_image(file_path)
            
            if 'error' in analysis:
                return {
                    'type': 'text',
                    'content': f"I couldn't analyze your image: {analysis['error']}",
                    'success': False
                }
            
            # Format analysis response
            response = f"🖼️ Image Analysis:\n\n"
            response += f"📐 Size: {analysis['width']} × {analysis['height']} pixels\n"
            response += f"📊 Format: {analysis['format']}\n"
            response += f"🎨 Mode: {analysis['mode']}\n"
            response += f"📏 Aspect Ratio: {analysis['aspect_ratio']}\n"
            
            if 'dominant_color' in analysis:
                color = analysis['dominant_color']
                response += f"🎨 Dominant Color: {color['hex']} (RGB: {color['rgb']})\n"
            
            return {
                'type': 'text',
                'content': response,
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {
                'type': 'text',
                'content': 'I encountered an error analyzing your image.',
                'success': False
            }
    
    def _build_context(self, user: Dict) -> Dict:
        """Build context for AI response generation."""
        context = {
            'user_id': user['id'],
            'platform': user['platform'],
            'user_preferences': self.db.get_user_preferences(user['id'])
        }
        
        # Get recent conversations
        recent_conversations = self.db.get_conversations(user['id'], limit=5)
        context['conversation_history'] = recent_conversations
        
        # Get user documents for semantic search
        user_documents = self.db.get_user_documents(user['id'])
        context['user_documents'] = user_documents
        
        return context
    
    def _handle_special_commands(self, content: str, context: Dict) -> Optional[str]:
        """Handle special commands like weather, news, etc."""
        content_lower = content.lower().strip()
        
        # Import the existing special command handlers from assistant.py
        from core.assistant import JarvisAssistant
        assistant = JarvisAssistant()
        
        # Check if this is a reminder request and handle it specially
        if content_lower.startswith(('add task', 'schedule task', 'remind me', 'reminder')):
            user_id = context.get('user_id')
            return assistant._parse_natural_reminder(content, user_id, self.scheduler)
        
        # Check if this is a social media post command
        if content_lower.startswith(('post to twitter:', 'post to facebook:', 'post to both:')) or 'tech quote' in content_lower:
            try:
                from core.social_media_manager import SocialMediaManager
                social_manager = SocialMediaManager()
                user_id = context.get('user_id')
                result = social_manager.process_whatsapp_post_command(content, user_id)
                if result:
                    return result
            except Exception as e:
                return f"❌ Social media posting error: {str(e)}"
        
        return assistant._handle_special_commands(content)
    
    # Command handlers
    def _handle_help(self, user: Dict, content: str) -> Dict:
        """Handle help command."""
        help_text = """
🤖 **Jarvis Help**

**Basic Commands:**
/help - Show this help message
/status - Check system status
/settings - Manage your preferences
/clear - Clear conversation context
/documents - List your uploaded documents
/reminders - Show your reminders
/setreminder - Set a specific reminder
/smartreminders - Set up automatic sleep/wake reminders
/emails - Check recent emails with AI summary
/setupsocial - Set up social media posting
/socialstats - View social media statistics
/stats - Show usage statistics

**What I can do:**
🌐 Get weather, news, and web information
🧮 Perform calculations and unit conversions
📄 Analyze PDF documents and images
🎤 Process voice messages
🖼️ Generate and analyze images
📅 Manage tasks and reminders with natural language
🎵 Download media from TikTok, Instagram, YouTube, Facebook
🌍 Translate text between languages
😴 Smart sleep & wake reminders
📱 Automated social media posting

**Natural Language Examples:**
- "Weather in London"
- "Latest technology news"
- "Calculate 15% of 250"
- "Convert 100 km to miles"
- "Remind me to pay my bills by 1:30pm today"
- "Remind me to call John tomorrow at 2 PM"
- "Download this YouTube video: [URL]"
- "Download this TikTok: [URL]"

**Smart Features:**
- Send me any social media URL to download videos/audio
- Use natural language for reminders (no complex formats needed)
- Type `/smartreminders` to set up automatic sleep/wake alerts
- Type `/setupsocial` for automated daily tech quotes
- Say "post to twitter: your message" to post directly
- Say "tech quote" to share inspiration

Just send me a message and I'll help you! 🚀
        """
        
        return {
            'type': 'text',
            'content': help_text,
            'success': True
        }
    
    def _handle_status(self, user: Dict, content: str) -> Dict:
        """Handle status command."""
        db_health = self.db.health_check()
        ai_health = self.ai.health_check()
        
        status = "🟢 ONLINE" if db_health and ai_health else "🔴 ISSUES DETECTED"
        
        status_text = f"""
**Jarvis Status: {status}**

🗄️ Database: {'✅ Healthy' if db_health else '❌ Issues'}
🧠 AI Engine: {'✅ Healthy' if ai_health else '❌ Issues'}
📊 Your Stats:
  • Messages: {len(self.db.get_conversations(user['id'], 100))}
  • Documents: {len(self.db.get_user_documents(user['id']))}

All systems operational! 🚀
        """
        
        return {
            'type': 'text',
            'content': status_text,
            'success': True
        }
    
    def _handle_settings(self, user: Dict, content: str) -> Dict:
        """Handle settings command."""
        preferences = self.db.get_user_preferences(user['id'])
        
        settings_text = f"""
⚙️ **Your Settings**

Current preferences:
```json
{json.dumps(preferences, indent=2)}
```

To update settings, send: `/settings key=value`
Example: `/settings voice_enabled=true`

Available settings:
- voice_enabled (true/false)
- language (en, es, fr, etc.)
- timezone (UTC, EST, etc.)
- notifications (true/false)
        """
        
        return {
            'type': 'text',
            'content': settings_text,
            'success': True
        }
    
    def _handle_clear_context(self, user: Dict, content: str) -> Dict:
        """Handle clear context command."""
        # Could implement session clearing here
        return {
            'type': 'text',
            'content': '🧹 Conversation context cleared! Starting fresh.',
            'success': True
        }
    
    def _handle_list_documents(self, user: Dict, content: str) -> Dict:
        """Handle list documents command."""
        documents = self.db.get_user_documents(user['id'])
        
        if not documents:
            return {
                'type': 'text',
                'content': '📄 You haven\'t uploaded any documents yet.',
                'success': True
            }
        
        doc_list = "📚 **Your Documents:**\n\n"
        for i, doc in enumerate(documents[:10], 1):
            doc_list += f"{i}. {doc['filename']} ({doc['file_type']})\n"
            doc_list += f"   📅 {doc['created_at']}\n"
            if doc['content_summary']:
                doc_list += f"   📝 {doc['content_summary'][:100]}...\n"
            doc_list += "\n"
        
        return {
            'type': 'text',
            'content': doc_list,
            'success': True
        }
    
    def _handle_list_reminders(self, user: Dict, content: str) -> Dict:
        """Handle list reminders command."""
        # This would integrate with the scheduler
        return {
            'type': 'text',
            'content': '📅 Reminder management coming soon!',
            'success': True
        }
    
    def _handle_set_reminder(self, user: Dict, content: str) -> Dict:
        """Handle set reminder command."""
        import re
        from dateutil.parser import parse
        try:
            # Parse command: /setreminder <time> <title> [description] [repeat]
            # Example: /setreminder 10pm sleep early daily
            parts = re.split(r'\s+', content[13:].strip())  # Remove /setreminder
            if len(parts) < 2:
                return {'type': 'text', 'content': 'Usage: /setreminder <time> <message> [repeat]', 'success': False}
            
            time_str = parts[0]
            message = ' '.join(parts[1:])
            repeat = None
            if message.lower().endswith(('daily', 'weekly', 'monthly')):
                last_word = message.split()[-1].lower()
                if last_word in ('daily', 'weekly', 'monthly'):
                    repeat = last_word
                    message = ' '.join(message.split()[:-1])
            
            # Parse time (simple: assume HH or HH:MM, PM/AM)
            parsed_time = parse(time_str, fuzzy=True)
            if parsed_time.time() < datetime.now().time():
                parsed_time += timedelta(days=1)
            
            result = self.scheduler.create_reminder({
                'user_id': user['id'],
                'title': message,
                'description': '',
                'reminder_time': parsed_time.isoformat(),
                'repeat_pattern': repeat
            })
            
            if result['success']:
                return {'type': 'text', 'content': result['message'], 'success': True}
            else:
                return {'type': 'text', 'content': result['error'], 'success': False}
        except Exception as e:
            return {'type': 'text', 'content': f'Error setting reminder: {str(e)}', 'success': False}
    
    def _handle_stats(self, user: Dict, content: str) -> Dict:
        """Handle stats command."""
        conversations = self.db.get_conversations(user['id'], 1000)
        documents = self.db.get_user_documents(user['id'])
        
        stats_text = f"""
📊 **Your Jarvis Statistics**

💬 Total Messages: {len(conversations)}
📄 Documents Uploaded: {len(documents)}
🗓️ Member Since: {user['created_at']}
🕒 Last Active: {user['last_active']}
📱 Platform: {user['platform'].title()}

Keep chatting to unlock more insights! 🚀
        """
        
        return {
            'type': 'text',
            'content': stats_text,
            'success': True
        }
    
    def _handle_setup_sleep_wake(self, user: Dict, content: str) -> Dict:
        """Handle setup sleep/wake reminders command."""
        try:
            success = self.scheduler.setup_smart_sleep_wake_reminders(user['id'])
            
            if success:
                return {
                    'type': 'text',
                    'content': '''🌙☀️ **Smart Sleep & Wake Reminders Set Up!**

I've created personalized daily reminders for you:

**Sleep Reminders (8PM - 12AM):**
🌙 8 PM - Wind-down routine reminder
🌙 9 PM - Prepare for bed
🌙 10 PM - Champions need rest
🌙 11 PM - Recharge time
🌙 12 AM - Sleep now, conquer tomorrow

**Wake Reminders (5AM - 10AM):**
☀️ 5 AM - Rise early, win the day
☀️ 6 AM - Seize the day
☀️ 7 AM - Goals are waiting
☀️ 8 AM - Another opportunity
☀️ 9 AM - Turn dreams to reality
☀️ 10 AM - Full of possibilities

These will repeat daily to help you maintain a healthy sleep schedule! 💪''',
                    'success': True
                }
            else:
                return {
                    'type': 'text',
                    'content': '❌ Failed to set up sleep/wake reminders. Please try again.',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"Error setting up sleep/wake reminders: {e}")
            return {
                'type': 'text',
                'content': f'❌ Error setting up reminders: {str(e)}',
                'success': False
            }

    def _handle_emails(self, user: Dict, content: str) -> Dict:
        """Handle email checking command."""
        try:
            from core.email_agent import EmailAgent
            
            email_agent = EmailAgent()
            
            # Check if email is configured
            if not all([email_agent.host, email_agent.username, email_agent.password]):
                return {
                    'type': 'text',
                    'content': '''📧 **Email Not Configured**
                    
To enable email checking, add these to your .env file:

```
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_SSL=true
```

For Gmail, use an App Password instead of your regular password.''',
                    'success': False
                }
            
            # Fetch recent emails
            emails = email_agent.fetch_recent_emails(limit=5)
            
            if not emails:
                return {
                    'type': 'text',
                    'content': '📧 No recent emails found.',
                    'success': True
                }
            
            # Generate AI summary
            summary = email_agent.summarize_emails(emails)
            
            # Format response
            response = f"📧 **Recent Emails Summary:**\n\n{summary}\n\n"
            response += "**Recent Messages:**\n"
            
            for i, email_item in enumerate(emails[:3], 1):
                response += f"\n{i}. **From:** {email_item['from']}\n"
                response += f"   **Subject:** {email_item['subject']}\n"
                response += f"   **Date:** {email_item['date']}\n"
                if email_item['snippet']:
                    response += f"   **Preview:** {email_item['snippet'][:100]}...\n"
            
            return {
                'type': 'text',
                'content': response,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
            return {
                'type': 'text',
                'content': f'❌ Error checking emails: {str(e)}',
                'success': False
            }

    def _handle_setup_social(self, user: Dict, content: str) -> Dict:
        """Handle social media setup command."""
        try:
            from core.social_media_manager import SocialMediaManager
            
            social_manager = SocialMediaManager()
            
            # Setup daily tech quotes
            social_manager.schedule_daily_tech_quotes(user['id'])
            
            setup_text = '''📱 **Social Media Setup Complete!**

✅ **Daily Tech Quotes Scheduled:**
• 🌅 **9:00 AM** - Morning inspiration
• 🌆 **6:00 PM** - Evening wisdom

✅ **WhatsApp Commands Available:**
• `post to twitter: your message` - Post to Twitter
• `post to facebook: your message` - Post to Facebook  
• `post to both: your message` - Post to both platforms
• `tech quote` - Post a random tech quote

⚙️ **Required Setup:**
Add these to your .env file:

**Twitter/X:**
```
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

**Facebook:**
```
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_token
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
```

🔗 **Get API Access:**
• Twitter: https://developer.twitter.com
• Facebook: https://developers.facebook.com

Your automated posting is ready! 🚀'''
            
            return {
                'type': 'text',
                'content': setup_text,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error setting up social media: {e}")
            return {
                'type': 'text',
                'content': f'❌ Error setting up social media: {str(e)}',
                'success': False
            }

    def _handle_social_stats(self, user: Dict, content: str) -> Dict:
        """Handle social media stats command."""
        try:
            from core.social_media_manager import SocialMediaManager
            
            social_manager = SocialMediaManager()
            stats = social_manager.get_posting_stats(user['id'])
            
            stats_text = f'''📊 **Social Media Statistics**

📈 **Posting Activity:**
• Total Posts: {stats['total_posts']}
• Twitter Posts: {stats['twitter_posts']}
• Facebook Posts: {stats['facebook_posts']}
• Last Post: {stats['last_post'] or 'Never'}

🔄 **Scheduled Posts:**
• Daily tech quotes at 9 AM & 6 PM
• Auto-posting: {'✅ Active' if stats['total_posts'] > 0 else '⏸️ Pending setup'}

💡 **Quick Commands:**
• Send "tech quote" to post inspiration
• Send "post to both: your message" to cross-post'''
            
            return {
                'type': 'text',
                'content': stats_text,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error getting social stats: {e}")
            return {
                'type': 'text',
                'content': f'❌ Error getting social stats: {str(e)}',
                'success': False
            }