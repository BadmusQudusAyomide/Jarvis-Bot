"""
WhatsApp Business API Integration for Jarvis Assistant

This module implements WhatsApp Business API integration using Meta's official API.
It provides webhook endpoints and message handling for WhatsApp conversations.
"""

import os
import logging
import requests
import tempfile
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import sys
import mimetypes
import re
import shutil
from urllib.parse import quote
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.assistant import JarvisAssistant
from core.database import DatabaseManager
from core.scheduler import SchedulerManager
from core.email_agent import EmailAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WhatsAppBot:
    """
    WhatsApp Business API integration for Jarvis Assistant.
    Uses Meta's official WhatsApp Business API.
    """
    
    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
        
        if not all([self.access_token, self.phone_number_id, self.verify_token]):
            raise ValueError("Missing required WhatsApp environment variables")
        
        self.assistant = JarvisAssistant()
        self.email_agent = EmailAgent()
        
        # scheduler_startup_fixed - Initialize scheduler for reminders
        self.db = DatabaseManager()
        self.scheduler_manager = SchedulerManager(self.db)
        self.scheduler_manager.start()
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook for WhatsApp Business API.
        
        Args:
            mode (str): Verification mode
            token (str): Verification token
            challenge (str): Challenge string
            
        Returns:
            str: Challenge if verification successful, None otherwise
        """
        try:
            if mode == "subscribe" and token == self.verify_token:
                logger.info("WhatsApp webhook verified successfully")
                return challenge
            else:
                logger.warning("WhatsApp webhook verification failed")
                return None
                
        except Exception as e:
            logger.error(f"Error verifying WhatsApp webhook: {e}")
            return None
    
    def send_text_message(self, phone_number: str, message: str) -> bool:
        """
        Send a text message via WhatsApp Business API.
        
        Args:
            phone_number (str): Recipient's phone number
            message (str): Message to send
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp message sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False
    
    def send_voice_message(self, phone_number: str, audio_file_path: str) -> bool:
        """
        Send a voice message via WhatsApp Business API.
        
        Args:
            phone_number (str): Recipient's phone number
            audio_file_path (str): Path to audio file
            
        Returns:
            bool: True if voice message sent successfully
        """
        try:
            # First upload the audio file to get media ID
            media_id = self._upload_media(audio_file_path, "audio")
            
            if not media_id:
                return False
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "audio",
                "audio": {"id": media_id}
            }
            
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp voice message sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp voice message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp voice message: {e}")
            return False
    
    def handle_incoming_message(self, webhook_data: Dict[str, Any]) -> None:
        """
        Handle incoming WhatsApp message from webhook.
        
        Args:
            webhook_data (dict): Webhook data from WhatsApp
        """
        try:
            # Extract message from webhook data
            entry = webhook_data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                return
            
            message = messages[0]
            sender = message.get('from', '')
            message_type = message.get('type', 'text')
            
            logger.info(f"Received {message_type} message from {sender}")
            
            if message_type == 'text':
                self._handle_text_message(sender, message)
            elif message_type == 'audio':
                self._handle_voice_message(sender, message)
            elif message_type == 'document':
                self._handle_document_message(sender, message)
            else:
                # Send unsupported message type response
                self.send_text_message(
                    sender, 
                    "I can currently handle text messages, voice notes, and PDF documents. "
                    "Please send one of these message types."
                )
                
        except Exception as e:
            logger.error(f"Error handling incoming WhatsApp message: {e}")
    
    def _handle_text_message(self, sender: str, message: Dict[str, Any]) -> None:
        """
        Handle incoming text message.
        
        Args:
            sender (str): Sender's phone number
            message (dict): Message data
        """
        try:
            message_text = message.get('text', {}).get('body', '')
            
            # Handle commands
            if message_text.lower().startswith('/'):
                self._handle_command(sender, message_text)
                return
            
            # Natural language reminders: "Remind me to <title> at YYYY-MM-DD HH:MM"
            try:
                import re
                # Strip chat export prefixes like "[9/15, 1:16 PM] Name: " or "9/15, 1:16 PM] Name: "
                cleaned = message_text.strip()
                # Remove optional leading timestamp + name prefix
                cleaned = re.sub(
                    r'^[\[]?\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*,\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\s*\]?\s*[\u200e\u200f]?\s*[^:：]*[:：]\s*',
                    '',
                    cleaned
                )
                m1 = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(today|tomorrow)\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)', cleaned, re.IGNORECASE)
                # time-first variant: "by 1:30pm today"
                m1b = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)\s+(today|tomorrow)\b', cleaned, re.IGNORECASE)
                m2 = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)\b', cleaned, re.IGNORECASE)
                m3 = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(\d{4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2})', cleaned, re.IGNORECASE)
                title = None
                time_tuple = None
                if m1:
                    title = m1.group(1).strip()
                    time_tuple = (m1.group(2).lower(), m1.group(3).strip())
                elif m1b:
                    title = m1b.group(1).strip()
                    time_tuple = (m1b.group(3).lower(), m1b.group(2).strip())
                elif m2:
                    title = m2.group(1).strip()
                    time_tuple = (None, m2.group(2).strip())
                elif m3:
                    title = m3.group(1).strip()
                    time_tuple = (m3.group(2).strip(), m3.group(3).strip())
                if time_tuple:
                    from datetime import datetime, timedelta
                    def to_datetime(pair):
                        if pair[0] in ('today', 'tomorrow'):
                            base = datetime.now()
                            if pair[0] == 'tomorrow':
                                base += timedelta(days=1)
                            hm = pair[1].lower().replace(' ', '')
                            ampm = 'am' if 'am' in hm or 'pm' in hm else None
                            hm = hm.replace('am','').replace('pm','')
                            hour, minute = map(int, hm.split(':'))
                            if ampm == 'pm' and hour < 12:
                                hour += 12
                            if ampm == 'am' and hour == 12:
                                hour = 0
                            return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if pair[0] is None:
                            base = datetime.now()
                            hm = pair[1].lower().replace(' ', '')
                            ampm = 'am' if 'am' in hm or 'pm' in hm else None
                            hm = hm.replace('am','').replace('pm','')
                            hour, minute = map(int, hm.split(':'))
                            if ampm == 'pm' and hour < 12:
                                hour += 12
                            if ampm == 'am' and hour == 12:
                                hour = 0
                            dt = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            if dt < base:
                                dt += timedelta(days=1)
                            return dt
                        return datetime.fromisoformat(f"{pair[0]} {pair[1]}")
                    reminder_dt = to_datetime(time_tuple)
                    # Ensure DB user exists
                    if not hasattr(self, 'db') or self.db is None:
                        self.db = DatabaseManager()
                    if not hasattr(self, 'scheduler_manager') or self.scheduler_manager is None:
                        self.scheduler_manager = SchedulerManager(self.db)
                        self.scheduler_manager.start()
                    user = self.db.get_or_create_user(
                        platform_id=sender,
                        platform='whatsapp',
                        username=sender
                    )
                    reminder_data = {
                        'user_id': user['id'],
                        'title': title,
                        'description': '',
                        'reminder_time': reminder_dt.isoformat(),
                        'repeat_pattern': None,
                        'platform': 'whatsapp',
                        'platform_id': sender
                    }
                    # reminder_platform_fixed - marker for fix detection
                    result = self.scheduler_manager.create_reminder(reminder_data)
                    if result.get('success'):
                        self.send_text_message(sender, f"✅ Reminder set for {result['scheduled_time']}\nTitle: {title}")
                    else:
                        self.send_text_message(sender, f"❌ Could not create reminder: {result.get('error','unknown error')}")
                    return
            except Exception as e:
                logger.error(f"WhatsApp reminder parse error: {e}")

            # Image generation command: !image <prompt>
            if message_text.lower().startswith('!image'):
                try:
                    prompt = message_text[6:].strip()
                    if not prompt:
                        self.send_text_message(sender, "Usage: !image your prompt here")
                        return
                    self.send_text_message(sender, "🎨 Generating image... This may take ~10–20s")
                    from core.assistant import JarvisAssistant
                    assistant = self.assistant
                    img_path = assistant.generate_image_file(prompt)
                    if img_path and os.path.exists(img_path):
                        media_id = self._upload_media(img_path, "image")
                        if media_id:
                            payload = {
                                "messaging_product": "whatsapp",
                                "to": sender,
                                "type": "image",
                                "image": {"id": media_id, "caption": f"Image: {prompt}"}
                            }
                            requests.post(self.base_url, headers=self.headers, json=payload)
                        else:
                            self.send_text_message(sender, "Generated image but failed to upload.")
                        try:
                            os.remove(img_path)
                        except Exception:
                            pass
                    else:
                        self.send_text_message(sender, "Sorry, I couldn't generate an image right now.")
                except Exception as e:
                    logger.error(f"Error generating image: {e}")
                    self.send_text_message(sender, "An error occurred while generating the image.")
                return
            
            # Check for YouTube links (robust detection) and extract the first URL
            import re
            youtube_patterns = [r'youtube\.com', r'youtu\.be', r'm\.youtube\.com']
            if any(re.search(pattern, message_text, re.IGNORECASE) for pattern in youtube_patterns):
                # Progress message
                self.send_text_message(sender, "⬇️ Downloading the video for you...")
                url_match = re.search(r'https?://\S+', message_text)
                if not url_match:
                    self.send_text_message(sender, "I couldn't find a valid YouTube URL in your message.")
                    return
                url = url_match.group(0)
                logger.info(f"Detected YouTube URL from WhatsApp: {url}")
                
                from core.youtube_utils import YouTubeDownloader
                downloader = YouTubeDownloader()
                
                # Download at 240p to fit WhatsApp media size limits
                file_path, error = downloader.download_video(url, quality='240p')
                
                if file_path:
                    try:
                        # Send video file back to the user
                        sent_ok = self._send_video_file(sender, file_path)
                        if not sent_ok:
                            self.send_text_message(sender, "I downloaded the video but couldn't send it. It may be too large.")
                    finally:
                        # Always clean up
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as cleanup_err:
                            logger.warning(f"Cleanup failed for {file_path}: {cleanup_err}")
                    return
                else:
                    # If video failed, try sending audio as a fallback
                    try:
                        audio_path, audio_error = downloader.download_audio(url)
                        if audio_path:
                            media_id = self._upload_media(audio_path, "audio")
                            if media_id:
                                payload = {
                                    "messaging_product": "whatsapp",
                                    "to": sender,
                                    "type": "audio",
                                    "audio": {"id": media_id}
                                }
                                requests.post(self.base_url, headers=self.headers, json=payload)
                            else:
                                self.send_text_message(sender, "Downloaded audio but failed to upload it to WhatsApp.")
                        else:
                            self.send_text_message(sender, f"Failed to download video: {error}")
                    finally:
                        try:
                            if 'audio_path' in locals() and audio_path and os.path.exists(audio_path):
                                os.remove(audio_path)
                        except Exception as cleanup_err:
                            logger.warning(f"Cleanup failed for {audio_path}: {cleanup_err}")
                    return
            
            # Instagram/TikTok links
            ig_tt_patterns = [r'instagram\.com', r'instagr\.am', r'tiktok\.com', r'vm\.tiktok\.com']
            if any(re.search(pattern, message_text, re.IGNORECASE) for pattern in ig_tt_patterns):
                # Progress message
                self.send_text_message(sender, "⬇️ Downloading the video for you...")
                url_match = re.search(r'https?://\S+', message_text)
                if not url_match:
                    self.send_text_message(sender, "I couldn't find a valid Instagram/TikTok URL in your message.")
                    return
                url = url_match.group(0)
                logger.info(f"Detected IG/TikTok URL from WhatsApp: {url}")
                from core.youtube_utils import YouTubeDownloader
                downloader = YouTubeDownloader()
                file_path, error = downloader.download_video(url, quality='240p')
                if file_path:
                    try:
                        sent_ok = self._send_video_file(sender, file_path)
                        if not sent_ok:
                            self.send_text_message(sender, "I downloaded the video but couldn't send it. It may be too large.")
                    finally:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as cleanup_err:
                            logger.warning(f"Cleanup failed for {file_path}: {cleanup_err}")
                    return
                else:
                    self.send_text_message(sender, f"Failed to download video: {error}")
                    return
            
            # Process with assistant
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
                self.send_text_message(sender, fallback_response)
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp text message: {e}")
            self.send_text_message(sender, "Sorry, I encountered an error processing your message.")
    
    def _handle_voice_message(self, sender: str, message: Dict[str, Any]) -> None:
        """
        Handle incoming voice message.
        
        Args:
            sender (str): Sender's phone number
            message (dict): Message data
        """
        try:
            # Download voice message
            audio_id = message.get('audio', {}).get('id', '')
            
            if not audio_id:
                self.send_text_message(sender, "Sorry, I couldn't process your voice message.")
                return
            
            # Download and process voice message
            voice_file_path = self.download_media(audio_id)
            
            if voice_file_path:
                transcribed_text, ai_response = self.assistant.process_voice_message(voice_file_path)
                
                # Send transcription and response
                if transcribed_text and transcribed_text != "Could not understand the audio.":
                    self.send_text_message(sender, f"🎤 You said: \"{transcribed_text}\"")
                
                self.send_text_message(sender, ai_response)
                
                # Clean up downloaded file
                os.unlink(voice_file_path)
            else:
                self.send_text_message(sender, "Sorry, I had trouble downloading your voice message.")
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp voice message: {e}")
            self.send_text_message(sender, "Sorry, I had trouble processing your voice message.")
    
    def _send_video_file(self, sender: str, file_path: str) -> bool:
        """
        Send a video file via WhatsApp Business API.
        
        Args:
            sender (str): Recipient's phone number
            file_path (str): Path to video file
            
        Returns:
            bool: True if video sent successfully
        """
        try:
            # Prefer direct upload (most reliable for inline rendering)
            media_id = self._upload_media(file_path, "video")
            if media_id:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": sender,
                    "type": "video",
                    "video": {
                        "id": media_id,
                        "caption": "Here's the video you requested"
                    }
                }
                response = requests.post(self.base_url, headers=self.headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"WhatsApp video (upload) sent successfully to {sender}")
                    return True
                else:
                    logger.error(f"Failed to send WhatsApp video (upload): {response.text}")
            else:
                logger.error("Upload returned no media_id; will try link fallback")

            # Fallback: send by public link if configured
            public_base = os.getenv('PUBLIC_BASE_URL')
            if public_base:
                from urllib.parse import quote
                # Create a safe filename (no spaces/specials) to serve via /media
                downloads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'downloads')
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                safe_base = re.sub(r'[^A-Za-z0-9_-]+', '_', base_name)[:60] or 'video'
                safe_name = f"{safe_base}.mp4"
                safe_path = os.path.join(downloads_dir, safe_name)
                try:
                    if file_path != safe_path:
                        import shutil
                        shutil.copy2(file_path, safe_path)
                except Exception as e:
                    logger.warning(f"Could not copy to safe name: {e}")
                    safe_name = os.path.basename(file_path)
                link = f"{public_base.rstrip('/')}/media/{quote(safe_name)}"
                payload = {
                    "messaging_product": "whatsapp",
                    "to": sender,
                    "type": "video",
                    "video": {
                        "link": link,
                        "caption": "Here's the video you requested"
                    }
                }
                response = requests.post(self.base_url, headers=self.headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"WhatsApp video (link) sent successfully to {sender}: {link}")
                    return True
                else:
                    logger.error(f"Failed to send WhatsApp video by link: {response.text}")
                    return False
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp video: {e}")
            return False
            
    def _handle_document_message(self, sender: str, message: Dict[str, Any]) -> None:
        """
        Handle incoming document message.
        
        Args:
            sender (str): Sender's phone number
            message (dict): Message data
        """
        try:
            document = message.get('document', {})
            filename = document.get('filename', '')
            document_id = document.get('id', '')

            if not filename.lower().endswith('.pdf'):
                self.send_text_message(
                    sender,
                    "I can only process PDF documents. Please send a PDF file."
                )
                return

            # Download document
            doc_file_path = self.download_media(document_id)

            if doc_file_path:
                try:
                    # Summarize
                    summary = self.assistant.summarize_pdf(doc_file_path)
                    self.send_text_message(
                        sender,
                        f"📄 Summary of {filename}:\n\n{summary}"
                    )
                finally:
                    # Clean up downloaded file
                    try:
                        os.unlink(doc_file_path)
                    except Exception:
                        pass
            else:
                self.send_text_message(sender, "Sorry, I had trouble downloading your document.")

        except Exception as e:
            logger.error(f"Error handling WhatsApp document: {e}")
            self.send_text_message(sender, "Sorry, I had trouble processing your document.")
    
    def download_media(self, media_id: str) -> Optional[str]:
        """
        Download media file from WhatsApp Business API.
        
        Args:
            media_id (str): Media file ID
            
        Returns:
            str: Path to downloaded file, or None if failed
        """
        try:
            # Get media URL
            media_url_response = requests.get(
                f"https://graph.facebook.com/v18.0/{media_id}",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            
            if media_url_response.status_code != 200:
                logger.error(f"Failed to get media URL: {media_url_response.text}")
                return None
            
            media_url = media_url_response.json().get('url')
            
            if not media_url:
                logger.error("No media URL found in response")
                return None
            
            # Download the actual media file
            media_response = requests.get(
                media_url,
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            
            if media_response.status_code != 200:
                logger.error(f"Failed to download media: {media_response.status_code}")
                return None
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(media_response.content)
                return temp_file.name
            
        except Exception as e:
            logger.error(f"Error downloading WhatsApp media: {e}")
            return None
    
    def _handle_command(self, sender: str, command: str) -> None:
        """
        Handle WhatsApp commands.
        
        Args:
            sender (str): Sender's phone number
            command (str): Command text
        """
        try:
            command = command.lower().strip()
            
            if command == '/start':
                welcome_message = """🤖 *Welcome to Jarvis!*

I'm your intelligent AI assistant, ready to help you with various tasks.

*What I can do:*
• Answer questions and provide information
• Process voice messages
• Read and analyze PDF documents
• Have natural conversations

*Available Commands:*
/start - Show this welcome message
/help - Get detailed help
/status - Check my status

Just send me a message or voice note to get started! 🚀"""
                self.send_text_message(sender, welcome_message)
                
            elif command == '/help':
                help_message = """📖 *Jarvis Help Guide*

*Text Messages:*
Simply type your question or request.

*Voice Messages:*
Send me a voice note, and I'll transcribe and respond.

*Document Analysis:*
Send me PDF files to add to my knowledge base.

*Commands:*
/start - Welcome message
/help - This help guide
/status - Check system status

Need more help? Just ask me anything! 💡"""
                self.send_text_message(sender, help_message)
                
            elif command == '/status':
                status_message = """✅ *Jarvis Status: ONLINE*
 
 🧠 AI Assistant: Active
 🎤 Voice Recognition: Ready
 📚 Knowledge Base: Ready
 🔗 WhatsApp Integration: Connected
 
 All systems operational! 🚀"""
                self.send_text_message(sender, status_message)
            elif command.startswith('/reminders'):
                try:
                    if not hasattr(self, 'db') or self.db is None:
                        self.db = DatabaseManager()
                    if not hasattr(self, 'scheduler_manager') or self.scheduler_manager is None:
                        self.scheduler_manager = SchedulerManager(self.db)
                        self.scheduler_manager.start()
                    user = self.db.get_or_create_user(platform_id=sender, platform='whatsapp', username=sender)
                    reminders = self.scheduler_manager.get_user_reminders(user['id'])
                    if not reminders:
                        self.send_text_message(sender, "You have no active reminders.")
                        return
                    lines = ["🗓️ Your active reminders:\n"]
                    for r in reminders[:15]:
                        rid = r.get('id')
                        title = r.get('title')
                        when = r.get('reminder_time')
                        next_time = r.get('next_run_time') or ''
                        if next_time:
                            lines.append(f"#{rid} • {title} • at {when} (next: {next_time})")
                        else:
                            lines.append(f"#{rid} • {title} • at {when}")
                    self.send_text_message(sender, "\n".join(lines))
                except Exception as e:
                    logger.error(f"/reminders error: {e}")
                    self.send_text_message(sender, "Sorry, I couldn't fetch your reminders.")
            elif command.startswith('/cancel'):
                try:
                    parts = command.split()
                    if len(parts) < 2:
                        self.send_text_message(sender, "Usage: /cancel <reminder_id>")
                        return
                    try:
                        reminder_id = int(parts[1])
                    except ValueError:
                        self.send_text_message(sender, "Reminder ID must be a number.")
                        return
                    if not hasattr(self, 'db') or self.db is None:
                        self.db = DatabaseManager()
                    if not hasattr(self, 'scheduler_manager') or self.scheduler_manager is None:
                        self.scheduler_manager = SchedulerManager(self.db)
                        self.scheduler_manager.start()
                    result = self.scheduler_manager.cancel_reminder(reminder_id)
                    if result.get('success'):
                        self.send_text_message(sender, f"✅ Cancelled reminder #{reminder_id}")
                    else:
                        self.send_text_message(sender, f"❌ Could not cancel: {result.get('error','unknown error')}")
                except Exception as e:
                    logger.error(f"/cancel error: {e}")
                    self.send_text_message(sender, "Sorry, I couldn't cancel that reminder.")
                
            elif command.startswith('/email_summary'):
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
                    self.send_text_message(sender, "I couldn't summarize your inbox. Check IMAP settings.")
            elif command.startswith('/email_draft'):
                try:
                    # Expected usage: reply to a previous message containing email context is not available on WhatsApp easily
                    # So we accept: /email_draft <instructions> \n\n<email context pasted after>
                    text = command[len('/email_draft'):].strip()
                    if not text:
                        self.send_text_message(sender, "Usage: /email_draft <instructions> then paste email content in next message.")
                        return
                    self.send_text_message(sender, "Okay. Please paste the email content to reply to.")
                    # In a simple flow, we cannot hold session here without storage; instruct the user instead
                    self.send_text_message(sender, "After pasting, send: /email_draft_go <instructions> <separator> <email content>")
                except Exception as e:
                    logger.error(f"/email_draft error: {e}")
                    self.send_text_message(sender, "I couldn't start drafting right now.")
            elif command.startswith('/email_draft_go'):
                try:
                    # Format: /email_draft_go instructions || email context
                    raw = command[len('/email_draft_go'):].strip()
                    if '||' not in raw:
                        self.send_text_message(sender, "Usage: /email_draft_go <instructions> || <email content>")
                        return
                    instructions, email_context = [p.strip() for p in raw.split('||', 1)]
                    if not hasattr(self, 'email_agent') or self.email_agent is None:
                        self.email_agent = EmailAgent()
                    draft = self.email_agent.draft_reply(email_context, instructions)
                    self.send_text_message(sender, f"✉️ Draft reply:\n\n{draft}")
                except Exception as e:
                    logger.error(f"/email_draft_go error: {e}")
                    self.send_text_message(sender, "I couldn't draft a reply right now.")
                
            else:
                self.send_text_message(sender, "Unknown command. Use /help to see available commands.")
                
        except Exception as e:
            logger.error(f"Error handling WhatsApp command: {e}")
            self.send_text_message(sender, "Sorry, I had trouble processing your command.")
    
    def _upload_media(self, file_path: str, media_type: str) -> Optional[str]:
        """
        Upload media file to WhatsApp Business API.
        
        Args:
            file_path (str): Path to media file
            media_type (str): Type of media (audio, document, etc.)
            
        Returns:
            str: Media ID if successful, None otherwise
        """
        try:
            upload_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/media"
            # Determine MIME type reliably
            guessed_mime, _ = mimetypes.guess_type(file_path)
            if not guessed_mime:
                # Fallbacks based on declared media_type
                if media_type == 'image':
                    guessed_mime = 'image/jpeg'
                elif media_type == 'video':
                    guessed_mime = 'video/mp4'
                elif media_type == 'audio':
                    guessed_mime = 'audio/mpeg'
                else:
                    guessed_mime = 'application/octet-stream'

            headers = {'Authorization': f'Bearer {self.access_token}'}
            with open(file_path, 'rb') as media_file:
                files = {
                    'file': (os.path.basename(file_path), media_file, guessed_mime)
                }
                data = {
                    'type': guessed_mime,
                    'messaging_product': 'whatsapp'
                }
                response = requests.post(upload_url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    return response.json().get('id')
                else:
                    logger.error(f"Failed to upload media: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None
    
    def run_webhook_server(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """
        Run Flask webhook server to receive WhatsApp messages.
        
        Args:
            host (str): Server host
            port (int): Server port
        """
        try:
            app = Flask(__name__)
            CORS(app)
            
            # Start scheduler on server start to enable reminders and periodic jobs
            try:
                self.db = DatabaseManager()
                self.scheduler_manager = SchedulerManager(self.db)
                self.scheduler_manager.start()
            except Exception as e:
                logger.error(f"Failed to start WhatsApp scheduler: {e}")

            # Schedule auto email summaries every 15 minutes for WhatsApp users
            try:
                from apscheduler.triggers.interval import IntervalTrigger
                def email_digest_job():
                    try:
                        # Get or create user preferences holder for the WhatsApp number configured via env
                        target_number = os.getenv('WHATSAPP_DIGEST_TO')
                        if not target_number:
                            return
                        user = self.db.get_or_create_user(platform_id=target_number, platform='whatsapp', username=target_number)
                        prefs = self.db.get_user_preferences(user['id'])
                        last_since = prefs.get('email_last_since')
                        from core.email_agent import EmailAgent
                        agent = EmailAgent()
                        from datetime import datetime, timedelta
                        if not last_since:
                            # default to today
                            since_lit = agent.to_imap_since(datetime.now())
                        else:
                            since_lit = last_since
                        emails = agent.fetch_new_since(since_lit)
                        if not emails:
                            return
                        # Summarize and send
                        summary = agent.summarize_emails(emails)
                        self.send_text_message(target_number, f"📬 Email digest:\n\n{summary}")
                        # Update last_since to today to avoid duplicates
                        prefs['email_last_since'] = agent.to_imap_since(datetime.now())
                        self.db.update_user_preferences(user['id'], prefs)
                    except Exception as e:
                        logger.error(f"Email digest job error: {e}")

                # add job (every 15 minutes)
                self.scheduler_manager.scheduler.add_job(
                    func=email_digest_job,
                    trigger=IntervalTrigger(minutes=15),
                    id='whatsapp_email_digest',
                    replace_existing=True
                )
            except Exception as e:
                logger.error(f"Failed to schedule email digest: {e}")
            
            # Optional: serve media files publicly for link sending
            @app.route('/media/<path:filename>', methods=['GET'])
            def serve_media(filename):
                from flask import send_from_directory
                downloads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'downloads')
                return send_from_directory(downloads_dir, filename, as_attachment=False)

            @app.route('/webhook', methods=['GET'])
            def verify_webhook():
                mode = request.args.get('hub.mode')
                token = request.args.get('hub.verify_token')
                challenge = request.args.get('hub.challenge')
                
                verification_result = self.verify_webhook(mode, token, challenge)
                
                if verification_result:
                    return verification_result
                else:
                    return 'Verification failed', 403
            
            @app.route('/webhook', methods=['POST'])
            def handle_webhook():
                try:
                    webhook_data = request.json
                    self.handle_incoming_message(webhook_data)
                    return jsonify({'status': 'success'}), 200
                except Exception as e:
                    logger.error(f"Error in webhook handler: {e}")
                    return jsonify({'status': 'error'}), 500
            
            @app.route('/health', methods=['GET'])
            def health_check():
                return jsonify({'status': 'healthy', 'service': 'Jarvis WhatsApp Bot'}), 200
            
            logger.info(f"Starting WhatsApp webhook server on {host}:{port}")
            logger.info(f"Webhook URL: http://{host}:{port}/webhook")
            
            app.run(host=host, port=port, debug=False)
            
        except Exception as e:
            logger.error(f"Error running WhatsApp webhook server: {e}")

def main():
    """
    Main function to run the WhatsApp bot webhook server.
    """
    try:
        logger.info("Starting WhatsApp Business API Bot...")
        bot = WhatsAppBot()
        bot.run_webhook_server()
        
    except KeyboardInterrupt:
        logger.info("WhatsApp bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
