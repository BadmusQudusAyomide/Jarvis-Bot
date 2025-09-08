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
    
    def __init__(self, database_manager, ai_engine):
        self.db = database_manager
        self.ai = ai_engine
        
        # Command handlers
        self.command_handlers = {
            'help': self._handle_help,
            'status': self._handle_status,
            'settings': self._handle_settings,
            'clear': self._handle_clear_context,
            'documents': self._handle_list_documents,
            'reminders': self._handle_list_reminders,
            'stats': self._handle_stats
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
/stats - Show usage statistics

**What I can do:**
🌐 Get weather, news, and web information
🧮 Perform calculations and unit conversions
📄 Analyze PDF documents and images
🎤 Process voice messages
🖼️ Generate and analyze images
📅 Manage tasks and reminders
🎵 Download media from URLs
🌍 Translate text between languages

**Examples:**
- "Weather in London"
- "Latest technology news"
- "Calculate 15% of 250"
- "Convert 100 km to miles"
- "Remind me to call John tomorrow at 2 PM"
- "Generate an image of a sunset"

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
