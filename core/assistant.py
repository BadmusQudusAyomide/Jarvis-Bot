import google.generativeai as genai
import os
from typing import Optional, Dict, Any
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
from .utils import PDFReader, TextToSpeech
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
        self.tts = TextToSpeech()
        self.recognizer = sr.Recognizer()
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
        """
        Process a voice message and return both transcription and AI response.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            tuple: (transcribed_text, ai_response)
        """
        try:
            # Convert audio to text
            transcribed_text = self._voice_to_text(audio_file_path)
            
            if not transcribed_text:
                return "Could not understand the audio.", "Please try speaking more clearly or send a text message."
            
            # Process the transcribed text
            ai_response = self.process_text_message(transcribed_text)
            
            return transcribed_text, ai_response
            
        except Exception as e:
            return "Error processing voice message.", f"I encountered an error: {str(e)}"
    
    def generate_voice_response(self, text: str) -> Optional[str]:
        """
        Convert text response to speech and return audio file path.
        
        Args:
            text (str): Text to convert to speech
            
        Returns:
            str: Path to generated audio file, or None if failed
        """
        try:
            return self.tts.text_to_speech(text)
        except Exception as e:
            print(f"Error generating voice response: {e}")
            return None
    
    def _voice_to_text(self, audio_file_path: str) -> Optional[str]:
        """
        Convert audio file to text using speech recognition.
        
        Args:
            audio_file_path (str): Path to audio file
            
        Returns:
            str: Transcribed text or None if failed
        """
        try:
            # Convert audio to WAV format if needed
            audio = AudioSegment.from_file(audio_file_path)
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                audio.export(temp_wav.name, format="wav")
                
                # Use speech recognition
                with sr.AudioFile(temp_wav.name) as source:
                    audio_data = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio_data)
                    
                # Clean up temporary file
                os.unlink(temp_wav.name)
                
                return text
                
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Speech recognition error: {e}")
            return None
        except Exception as e:
            print(f"Error in voice to text conversion: {e}")
            return None
    
    def _search_knowledge_base(self, query: str) -> str:
        """
        Search through PDF documents in knowledge base for relevant information.
        
        Args:
            query (str): Search query
            
        Returns:
            str: Relevant context from knowledge base
        """
        try:
            relevant_content = []
            
            # Get all PDF files in knowledge base
            for filename in os.listdir(self.knowledge_base_path):
                if filename.lower().endswith('.pdf'):
                    file_path = os.path.join(self.knowledge_base_path, filename)
                    content = self.pdf_reader.extract_text(file_path)
                    
                    # Simple keyword matching (can be improved with vector search)
                    if any(keyword.lower() in content.lower() for keyword in query.split()):
                        # Get relevant excerpt (first 500 chars containing keywords)
                        words = content.split()
                        for i, word in enumerate(words):
                            if any(keyword.lower() in word.lower() for keyword in query.split()):
                                start = max(0, i - 50)
                                end = min(len(words), i + 50)
                                excerpt = ' '.join(words[start:end])
                                relevant_content.append(f"From {filename}: {excerpt}")
                                break
            
            return '\n\n'.join(relevant_content[:3])  # Limit to 3 most relevant excerpts
            
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return ""
    
    def _build_system_prompt(self, knowledge_context: str = "") -> str:
        """
        Build system prompt for the AI assistant.
        
        Args:
            knowledge_context (str): Relevant context from knowledge base
            
        Returns:
            str: Complete system prompt
        """
        base_prompt = """You are Jarvis, an intelligent AI assistant. You are helpful, knowledgeable, and friendly.
        You can assist with various tasks including answering questions, providing information, and helping with problem-solving.
        
        Key characteristics:
        - Be concise but thorough in your responses
        - Show personality while remaining professional
        - If you don't know something, admit it honestly
        - Provide practical and actionable advice when possible"""
        
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
        
        # Task management
        if message_lower.startswith(('add task', 'schedule task', 'remind me')):
            return "To add a task, please provide: title, description, and due date (YYYY-MM-DD HH:MM)\n" \
                   "Example: 'Add task: Meeting with client, Discuss project requirements, 2024-01-15 14:30'"
        
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
        
        # YouTube Download
        if any(keyword in message_lower for keyword in ['download', 'youtube', 'video', 'audio']):
            url_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+)', message)
            if url_match:
                url = url_match.group(1)
                media_type = 'audio' if 'audio' in message_lower else 'video'
                
                # Use AI engine's download_media method
                from .ai_engine import AIEngine
                ai_engine = AIEngine()
                result = ai_engine.download_media(url, media_type)
                
                if result:
                    return f"✅ Successfully downloaded {media_type} from YouTube!\n📁 Saved to: {result}"
                else:
                    return f"❌ Failed to download {media_type} from YouTube. Please check the URL and try again."
        
        # Facebook Reels Download
        if any(keyword in message_lower for keyword in ['download', 'facebook', 'reel', 'video', 'audio']):
            url_match = re.search(r'(https?://(?:www\.)?facebook\.com/reel/\d+|https?://(?:www\.)?facebook\.com/.*/videos/\d+|https?://fb\.watch/[a-zA-Z0-9_-]+)/?', message)
            if url_match:
                url = url_match.group(1)
                media_type = 'audio' if 'audio' in message_lower else 'video'
                
                from .ai_engine import AIEngine
                ai_engine = AIEngine()
                result = ai_engine.download_media(url, media_type)
                
                if result:
                    return f"✅ Successfully downloaded {media_type} from Facebook!\n📁 Saved to: {result}"
                else:
                    return f"❌ Failed to download {media_type} from Facebook. Please check the URL and try again."

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
