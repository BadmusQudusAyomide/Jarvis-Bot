import google.generativeai as genai
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Speech recognition disabled for memory optimization
HAS_SPEECH_RECOGNITION = False
HAS_PYDUB = False
sr = None
AudioSegment = None

import tempfile
from .utils import PDFReader
from .web_tools import WebTools
from .advanced_features import CalculatorTools, TaskScheduler, ImageAnalyzer, TextAnalyzer
from dotenv import load_dotenv
import re
import requests

# Load environment variables
load_dotenv()

class JarvisAssistant:
    """
    Core AI Assistant class that handles all AI-related functionality.
    This is platform-independent and can be used with any messaging service.
    """
    
    def __init__(self):
        # Configure Gemini
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.pdf_reader = PDFReader()
        
        # Speech recognition and TTS disabled for memory optimization
        self.recognizer = None
            
        self.knowledge_base_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge_base')
        
        # Initialize new tools
        self.web_tools = WebTools()
        self.calculator = CalculatorTools()
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.task_scheduler = TaskScheduler(data_dir)
        self.image_analyzer = ImageAnalyzer()
        self.text_analyzer = TextAnalyzer()
        
        # Ensure directories exist
        os.makedirs(self.knowledge_base_path, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        
    
    def get_fallback_response(self, message: str) -> str:
        """
        Get fallback response when AI is unavailable.
        # fallback_responses_added - marker for fix detection
        """
        message_lower = message.lower().strip()
        
        # Handle common queries without AI
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return "👋 Hello! I'm having some AI processing issues right now, but I can still help with:\n\n• Social media: 'tech quote'\n• Downloads: Send YouTube/TikTok links\n• Commands: /help, /status"
        
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

    def generate_image_file(self, prompt: str) -> Optional[str]:
        """
        Generate an image file from a prompt using available providers.
        Uses AIEngine.generate_image (OpenAI DALL·E if configured). If a URL is returned, downloads it.
        Returns local file path or None.
        """
        try:
            from .ai_engine import AIEngine
            engine = AIEngine()
            result = engine.generate_image(prompt)
            if not result:
                return None
            # If result is already a local path
            if os.path.exists(result):
                return result
            # Otherwise, assume it's a URL; download to data/documents/generated
            out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'documents', 'generated')
            os.makedirs(out_dir, exist_ok=True)
            filename = re.sub(r'[^a-zA-Z0-9_-]+', '_', prompt.strip())[:40] or 'image'
            out_path = os.path.join(out_dir, f"{filename}.png")
            resp = requests.get(result, timeout=30)
            if resp.status_code == 200:
                with open(out_path, 'wb') as f:
                    f.write(resp.content)
                return out_path
            return None
        except Exception:
            return None
    def summarize_pdf(self, file_path: str, max_chars: int = 1200) -> str:
        """
        Extract text from a PDF and generate a concise summary.
        Falls back to a simple extractive summary if LLM fails.
        """
        try:
            content = self.pdf_reader.extract_text(file_path)
            if not content:
                return "I couldn't extract readable text from this PDF."
            # For large documents, chunk then summarize each chunk, then synthesize
            chunks = self._chunk_text(content, max_words_per_chunk=1000)
            chunk_summaries = []
            for idx, chunk in enumerate(chunks, 1):
                prompt = (
                    "You are a professional document summarizer. Your goal is to create a concise, "
                    "easy-to-read summary of the provided text. The summary must capture the main ideas and key details. "
                    "Do not include any information that is not in the original text.\n\n"
                    f"Text (chunk {idx}/{len(chunks)}):\n{chunk}\n\n"
                    "Return 3-6 bullet points. Keep each bullet to one sentence."
                )
                summary_text = self._llm_summarize(prompt)
                if summary_text:
                    chunk_summaries.append(summary_text)
            # If we have multiple chunk summaries, synthesize a final concise summary
            if chunk_summaries:
                synthesis_prompt = (
                    "You are a professional document summarizer. Merge the bullet points below into a single, "
                    "clean summary with 5-7 bullets, no redundancy, preserving only information present in the bullets.\n\n"
                    "Bullets to merge:\n" + "\n".join(chunk_summaries)
                )
                final_summary = self._llm_summarize(synthesis_prompt)
                if final_summary:
                    # Trim to soft limit
                    final_summary = final_summary.strip()
                    if len(final_summary) > max_chars:
                        final_summary = final_summary[:max_chars] + "..."
                    return final_summary
            # Fallback simple extractive summary on first chunk
            first = chunks[0] if chunks else content
            sentences = first.split('. ')
            fallback = '\n'.join([f"- {s.strip()}" for s in sentences[:5] if s.strip()])
            if not fallback:
                fallback = first[:max_chars]
            if len(fallback) > max_chars:
                fallback = fallback[:max_chars] + "..."
            return fallback
        except Exception as e:
            return f"Error summarizing PDF: {e}"

    def _chunk_text(self, text: str, max_words_per_chunk: int = 1000) -> list[str]:
        """Split large text into word-based chunks to fit LLM limits."""
        try:
            words = text.split()
            chunks = []
            for i in range(0, len(words), max_words_per_chunk):
                chunk_words = words[i:i + max_words_per_chunk]
                chunks.append(' '.join(chunk_words))
            return chunks if chunks else [text]
        except Exception:
            return [text]

    def _llm_summarize(self, prompt: str) -> str | None:
        """Call the configured LLM to summarize; return None on failure."""
        try:
            response = self.model.generate_content(prompt)
            text = (response.text or '').strip()
            return text or None
        except Exception:
            return None

    def process_text_message(self, message: str, user_context: Optional[Dict] = None) -> str:
        """
        Process a text message and return AI response.
        
        Args:
            message (str): The user's text message
            user_context (dict, optional): Additional context about the user
            
        Returns:
            str: AI-generated response
        """
        try:
            # Check for special commands first
            special_response = self._handle_special_commands(message)
            if special_response:
                return special_response
            
            # Check if message relates to knowledge base
            knowledge_context = self._search_knowledge_base(message)
            
            # Prepare system prompt
            system_prompt = self._build_system_prompt(knowledge_context)
            
            # Combine system prompt and user message for Gemini
            full_prompt = f"{system_prompt}\n\nUser: {message}\n\nAssistant:"
            
            # Generate response using Gemini
            response = self.model.generate_content(full_prompt)
            
            return response.text.strip()
            
        except Exception as e:
            return f"I apologize, but I encountered an error processing your message: {str(e)}"
    
    def process_voice_message(self, audio_file_path: str) -> tuple[str, str]:
        """Voice processing disabled for memory optimization."""
        return "Voice processing disabled.", "Please send text messages only. Voice features are disabled to optimize memory usage."
    
    def generate_voice_response(self, text: str) -> Optional[str]:
        """Voice generation disabled for memory optimization."""
        return None
    
    def _voice_to_text(self, audio_file_path: str) -> Optional[str]:
        """Voice to text disabled for memory optimization."""
        return None
    
    def _search_knowledge_base(self, query: str) -> str:
        """Advanced document search disabled for memory optimization."""
        return ""
    
    def _build_system_prompt(self, knowledge_context: str = "") -> str:
        """
        Build system prompt for the AI assistant.
        
        Args:
            knowledge_context (str): Relevant context from knowledge base
            
        Returns:
            str: Complete system prompt
        """
        base_prompt = """You are Jarvis, a personal AI assistant for Badmus Qudus Ayomide (the creator).\n        - Always refer to yourself as Jarvis.\n        - Never mention underlying providers or models (e.g., Gemini, OpenAI).\n        - Be concise, helpful, and motivating when appropriate.\n        - Remember prior preferences and conversation context when available.\n        - Offer practical, actionable steps.\n        - If unsure, say so briefly and propose next steps."""
        
        if knowledge_context:
            base_prompt += f"\n\nRelevant information from your knowledge base:\n{knowledge_context}\n\nUse this information to provide more accurate and detailed responses when relevant."
        
        return base_prompt
    
    def _handle_special_commands(self, message: str) -> Optional[str]:
        """
        Handle special commands and tools.
        
        Args:
            message (str): User message
            
        Returns:
            str: Response if special command handled, None otherwise
        """
        message_lower = message.lower().strip()
        
        # Weather command
        if message_lower.startswith(('weather', 'what\'s the weather', 'how\'s the weather')):
            location = self._extract_location(message) or 'London'
            weather = self.web_tools.get_weather(location)
            if 'error' in weather:
                return f"Sorry, I couldn't get weather information: {weather['error']}"
            return f"Weather in {weather['location']}:\n" \
                   f"🌡️ Temperature: {weather['temperature']}\n" \
                   f"☁️ Condition: {weather['condition']}\n" \
                   f"💧 Humidity: {weather['humidity']}\n" \
                   f"💨 Wind: {weather['wind']}\n" \
                   f"🌡️ Feels like: {weather['feels_like']}"
        
        # News command
        if message_lower.startswith(('news', 'latest news', 'headlines')):
            category = self._extract_news_category(message)
            headlines = self.web_tools.get_news_headlines(category, 3)
            if headlines and 'title' in headlines[0]:
                response = f"📰 Latest {category} news:\n\n"
                for i, headline in enumerate(headlines, 1):
                    response += f"{i}. {headline['title']}\n{headline['description'][:100]}...\n\n"
                return response
            return "Sorry, I couldn't fetch the latest news right now."
        
        # Calculator command
        if any(op in message for op in ['+', '-', '*', '/', '=', 'calculate', 'compute']):
            # Extract mathematical expression
            math_match = re.search(r'[0-9+\-*/().^%√πe\s]+', message)
            if math_match:
                expression = math_match.group().strip()
                if len(expression) > 2:  # Avoid single characters
                    result = self.calculator.evaluate_expression(expression)
                    if result['status'] == 'success':
                        return f"🧮 Calculation: {expression} = {result['formatted_result']}"
                    else:
                        return f"❌ {result['error']}"
        
        # Unit conversion
        convert_match = re.search(r'convert (\d+(?:\.\d+)?)\s*(\w+)\s*to\s*(\w+)', message_lower)
        if convert_match:
            value, from_unit, to_unit = convert_match.groups()
            result = self.calculator.convert_units(float(value), from_unit, to_unit)
            if result['status'] == 'success':
                return f"🔄 {value} {from_unit} = {result['formatted_result']} {to_unit}"
            else:
                return f"❌ {result['error']}"
        
        # Task management - Natural Language Reminder Processing
        if message_lower.startswith(('add task', 'schedule task', 'remind me', 'reminder')):
            return self._parse_natural_reminder(message)
        
        if message_lower.startswith('my tasks') or 'upcoming tasks' in message_lower:
            tasks = self.task_scheduler.get_upcoming_tasks()
            if tasks:
                response = "📅 Your upcoming tasks:\n\n"
                for task in tasks[:5]:  # Show max 5 tasks
                    response += f"• {task['title']} - Due: {task['due_date']} ({task['priority']} priority)\n"
                return response
            return "You have no upcoming tasks scheduled."
        
        # Web search
        if message_lower.startswith(('search', 'look up', 'find information about')):
            query = message[message.lower().find('search') + 6:].strip()
            if not query:
                query = message[message.lower().find('look up') + 7:].strip()
            if not query:
                query = message[message.lower().find('find information about') + 21:].strip()
            
            if query:
                results = self.web_tools.search_web(query, 2)
                if results:
                    response = f"🔍 Search results for '{query}':\n\n"
                    for i, result in enumerate(results, 1):
                        response += f"{i}. {result['title']}\n{result['snippet'][:150]}...\n\n"
                    return response
                return f"Sorry, I couldn't find information about '{query}' right now."
        
        # Cryptocurrency prices
        if 'crypto' in message_lower or 'bitcoin' in message_lower or 'ethereum' in message_lower:
            prices = self.web_tools.get_cryptocurrency_prices()
            if 'error' not in prices:
                response = "💰 Cryptocurrency Prices:\n\n"
                for coin, data in prices.items():
                    response += f"{coin.title()}: {data['price']} ({data['change_24h']})\n"
                return response
            return "Sorry, I couldn't fetch cryptocurrency prices right now."
        
        # Translation
        translate_match = re.search(r'translate ["\'](.+?)["\'] to (\w+)', message_lower)
        if translate_match:
            text, target_lang = translate_match.groups()
            translation = self.web_tools.translate_text(text, target_lang)
            if 'error' not in translation:
                return f"Translation: {translation['translated_text']}"
            return "Sorry, I couldn't translate that text right now."
        
        # Social Media Download - Enhanced with TikTok, Instagram, YouTube, Facebook
        if any(keyword in message_lower for keyword in ['download', 'youtube', 'tiktok', 'instagram', 'facebook', 'video', 'audio']):
            # YouTube URLs
            youtube_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+)', message)
            # TikTok URLs
            tiktok_match = re.search(r'(https?://(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)/[\w\-\./\?=&]+)', message)
            # Instagram URLs
            instagram_match = re.search(r'(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w-]+/?)', message)
            # Facebook URLs
            facebook_match = re.search(r'(https?://(?:www\.)?(?:facebook\.com|fb\.watch)/[\w\-\./\?=&]+)', message)
            
            url = None
            platform = None
            
            if youtube_match:
                url = youtube_match.group(1)
                platform = "YouTube"
            elif tiktok_match:
                url = tiktok_match.group(1)
                platform = "TikTok"
            elif instagram_match:
                url = instagram_match.group(1)
                platform = "Instagram"
            elif facebook_match:
                url = facebook_match.group(1)
                platform = "Facebook"
            
            if url and platform:
                media_type = 'audio' if 'audio' in message_lower else 'video'
                
                # Use AI engine's download_media method
                from .ai_engine import AIEngine
                ai_engine = AIEngine()
                result = ai_engine.download_media(url, media_type)
                
                if result:
                    return f"✅ Successfully downloaded {media_type} from {platform}!\n📁 Saved to: {result}"
                else:
                    return f"❌ Failed to download {media_type} from {platform}. Please check the URL and try again."

        # Text analysis
        if message_lower.startswith('analyze text:'):
            text_to_analyze = message[13:].strip()
            if text_to_analyze:
                analysis = self.text_analyzer.analyze_text(text_to_analyze)
                if analysis['status'] == 'success':
                    return f"📊 Text Analysis:\n" \
                           f"• Words: {analysis['word_count']}\n" \
                           f"• Characters: {analysis['character_count']}\n" \
                           f"• Sentences: {analysis['sentence_count']}\n" \
                           f"• Reading time: {analysis['estimated_reading_time_minutes']} min\n" \
                           f"• Avg words/sentence: {analysis['average_words_per_sentence']}"
                else:
                    return f"❌ {analysis['error']}"
        
        return None
    
    def _extract_location(self, message: str) -> Optional[str]:
        """Extract location from weather query."""
        # Simple location extraction - can be improved
        words = message.split()
        for i, word in enumerate(words):
            if word.lower() in ['in', 'for', 'at']:
                if i + 1 < len(words):
                    return ' '.join(words[i+1:]).strip('?.,!')
        return None
    
    def _extract_news_category(self, message: str) -> str:
        """Extract news category from message."""
        categories = ['technology', 'science', 'business', 'world', 'general']
        message_lower = message.lower()
        for category in categories:
            if category in message_lower:
                return category
        return 'general'
    
    def add_document_to_knowledge_base(self, file_path: str, filename: str) -> bool:
        """
        Add a document to the knowledge base.
        
        Args:
            file_path (str): Path to the source file
            filename (str): Desired filename in knowledge base
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import shutil
            destination = os.path.join(self.knowledge_base_path, filename)
            shutil.copy2(file_path, destination)
            return True
        except Exception as e:
            print(f"Error adding document to knowledge base: {e}")
            return False
    
    def _parse_natural_reminder(self, message: str, user_id: int = None, scheduler_manager=None) -> str:
        """
        Parse natural language reminder requests and create reminders.
        
        Examples:
        - "Remind me to pay my bills by 1:30pm today"
        - "Remind me to call John tomorrow at 2 PM"
        - "Set a reminder for meeting at 3:00 PM"
        """
        try:
            from datetime import datetime, timedelta
            import re
            
            message_lower = message.lower().strip()
            
            # Extract the task/reminder text
            task_patterns = [
                r'remind me to (.+?) (?:by|at|on) (.+)',
                r'remind me to (.+)',
                r'reminder (?:to )?(.+?) (?:by|at|on) (.+)',
                r'set (?:a )?reminder (?:for|to) (.+?) (?:by|at|on) (.+)',
                r'schedule (.+?) (?:for|at) (.+)'
            ]
            
            task_text = None
            time_text = None
            
            for pattern in task_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    if len(match.groups()) == 2:
                        task_text = match.group(1).strip()
                        time_text = match.group(2).strip()
                    else:
                        task_text = match.group(1).strip()
                        # Extract time from the rest of the message
                        time_patterns = [
                            r'(?:by|at|on) (.+)',
                            r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))',
                            r'(today|tomorrow|tonight)',
                        ]
                        for time_pattern in time_patterns:
                            time_match = re.search(time_pattern, message_lower)
                            if time_match:
                                time_text = time_match.group(1).strip()
                                break
                    break
            
            if not task_text:
                return "I couldn't understand what you want to be reminded about. Please try: 'Remind me to [task] by [time]'"
            
            # Parse time
            reminder_time = self._parse_time_expression(time_text or 'in 1 hour')
            
            if not reminder_time:
                return f"I couldn't understand the time '{time_text}'. Please use formats like '2:30 PM', 'tomorrow at 3 PM', or 'in 30 minutes'."
            
            # If scheduler_manager is provided (from message router), use it for proper reminders
            if scheduler_manager and user_id:
                result = scheduler_manager.create_reminder({
                    'user_id': user_id,
                    'title': task_text.title(),
                    'description': f"Reminder: {task_text}",
                    'reminder_time': reminder_time.isoformat(),
                    'repeat_pattern': None
                })
                
                if result['success']:
                    return f"✅ Reminder set! I'll remind you to {task_text} on {reminder_time.strftime('%B %d, %Y at %I:%M %p')}"
                else:
                    return f"❌ Failed to set reminder: {result.get('error', 'Unknown error')}"
            else:
                # Fallback to task scheduler for basic functionality
                result = self.task_scheduler.add_task(
                    title=task_text.title(),
                    description=f"Reminder: {task_text}",
                    due_date=reminder_time.strftime('%Y-%m-%d %H:%M'),
                    priority='medium'
                )
                
                if result['status'] == 'success':
                    return f"✅ Reminder set! I'll remind you to {task_text} on {reminder_time.strftime('%B %d, %Y at %I:%M %p')}"
                else:
                    return f"❌ Failed to set reminder: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"❌ Error setting reminder: {str(e)}. Please try: 'Remind me to [task] by [time]'"
    
    def _parse_time_expression(self, time_text: str) -> Optional[datetime]:
        """
        Parse various time expressions into datetime objects.
        """
        try:
            from datetime import datetime, timedelta
            import re
            
            if not time_text:
                return None
                
            time_text = time_text.lower().strip()
            now = datetime.now()
            
            # Handle "today" with time
            if 'today' in time_text:
                time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', time_text)
                if time_match:
                    time_str = time_match.group(1)
                    try:
                        if ':' in time_str:
                            parsed_time = datetime.strptime(time_str.replace(' ', ''), '%I:%M%p')
                        else:
                            parsed_time = datetime.strptime(time_str.replace(' ', ''), '%I%p')
                        return now.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
                    except:
                        pass
                else:
                    # Just "today" without specific time - default to 1 hour from now
                    return now + timedelta(hours=1)
            
            # Handle "tomorrow" with time
            if 'tomorrow' in time_text:
                time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', time_text)
                if time_match:
                    time_str = time_match.group(1)
                    try:
                        if ':' in time_str:
                            parsed_time = datetime.strptime(time_str.replace(' ', ''), '%I:%M%p')
                        else:
                            parsed_time = datetime.strptime(time_str.replace(' ', ''), '%I%p')
                        tomorrow = now + timedelta(days=1)
                        return tomorrow.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
                    except:
                        pass
                else:
                    # Just "tomorrow" without specific time - default to 9 AM
                    tomorrow = now + timedelta(days=1)
                    return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Handle specific times (e.g., "2:30 PM", "1:30pm")
            time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', time_text)
            if time_match:
                time_str = time_match.group(1)
                try:
                    if ':' in time_str:
                        parsed_time = datetime.strptime(time_str.replace(' ', ''), '%I:%M%p')
                    else:
                        parsed_time = datetime.strptime(time_str.replace(' ', ''), '%I%p')
                    
                    target_time = now.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
                    
                    # If the time has already passed today, schedule for tomorrow
                    if target_time <= now:
                        target_time += timedelta(days=1)
                    
                    return target_time
                except:
                    pass
            
            # Handle relative times ("in 30 minutes", "in 2 hours")
            relative_match = re.search(r'in (\d+)\s*(minute|hour|day)s?', time_text)
            if relative_match:
                amount = int(relative_match.group(1))
                unit = relative_match.group(2)
                
                if unit == 'minute':
                    return now + timedelta(minutes=amount)
                elif unit == 'hour':
                    return now + timedelta(hours=amount)
                elif unit == 'day':
                    return now + timedelta(days=amount)
            
            # Default fallback - 1 hour from now
            return now + timedelta(hours=1)
            
        except Exception as e:
            print(f"Error parsing time: {e}")
            return None
