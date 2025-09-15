import os
import logging
from typing import Optional
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import tempfile
from dotenv import load_dotenv
import time
import sys
import requests
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

class TelegramBot:
    """
    Telegram bot integration for Jarvis Assistant.
    Handles all Telegram-specific functionality and message routing.
    """
    
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.assistant = JarvisAssistant()
        self.application = None
        self.scheduler_manager = None
        self.db = None
        self.email_agent = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command - welcome message.
        """
        welcome_message = """
🤖 **Welcome to Jarvis!** 

I'm your intelligent AI assistant, ready to help you with various tasks.

**What I can do:**
• Answer questions and provide information
• Process voice messages (send me audio!)
• Read and analyze PDF documents you share
• Have natural conversations
• Help with problem-solving and research

**Available Commands:**
/start - Show this welcome message
/help - Get detailed help information
/status - Check my current status
/voice_on - Enable voice responses
/voice_off - Disable voice responses

Just send me a message or voice note to get started! 🚀
        """
        
        chat_id = str(update.effective_chat.id)
        tg_user = update.effective_user
        user = self.db.get_or_create_user(
            platform_id=chat_id,
            platform='telegram',
            username=getattr(tg_user, 'username', None),
            first_name=getattr(tg_user, 'first_name', None),
            last_name=getattr(tg_user, 'last_name', None)
        )
        # Ensure daily reminders are set without breaking /start if scheduler fails
        try:
            self.scheduler_manager.setup_daily_reminders(user['id'])
        except Exception as e:
            logger.warning(f"Could not setup daily reminders: {e}")
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command - detailed help information.
        """
        help_message = """
📖 **Jarvis Help Guide**

**Text Messages:**
Simply type your question or request, and I'll respond with helpful information.

**Voice Messages:**
Send me a voice note, and I'll:
1. Convert your speech to text
2. Process your request
3. Respond with both text and optional voice reply

**Document Analysis:**
Send me PDF files, and I'll add them to my knowledge base to provide more accurate answers about their content.

**Commands:**
/start - Welcome message and overview
/help - This detailed help guide
/status - Check system status
/voice_on - Enable voice responses (I'll reply with audio)
/voice_off - Disable voice responses (text only)

**Tips:**
• Speak clearly for better voice recognition
• Ask specific questions for more accurate answers
• I can remember information from uploaded documents
• Feel free to have natural conversations!

Need more help? Just ask me anything! 💡
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')

    async def reminders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        List active reminders for the current user.
        """
        try:
            # Ensure DB and scheduler
            if not self.db:
                self.db = DatabaseManager()
            if not self.scheduler_manager:
                self.scheduler_manager = SchedulerManager(self.db)
                self.scheduler_manager.start()

            chat_id = str(update.effective_chat.id)
            tg_user = update.effective_user
            user = self.db.get_or_create_user(
                platform_id=chat_id,
                platform='telegram',
                username=getattr(tg_user, 'username', None),
                first_name=getattr(tg_user, 'first_name', None),
                last_name=getattr(tg_user, 'last_name', None)
            )

            reminders = self.scheduler_manager.get_user_reminders(user['id'])
            if not reminders:
                await update.message.reply_text("You have no active reminders.")
                return
            lines = ["🗓️ Your active reminders:\n"]
            for r in reminders[:15]:
                when = r.get('reminder_time')
                rid = r.get('id')
                title = r.get('title')
                next_time = r.get('next_run_time') or ''
                if next_time:
                    lines.append(f"#{rid} • {title} • at {when} (next: {next_time})")
                else:
                    lines.append(f"#{rid} • {title} • at {when}")
            await update.message.reply_text("\n".join(lines))
        except Exception as e:
            logger.error(f"/reminders error: {e}")
            await update.message.reply_text("Sorry, I couldn't fetch your reminders.")

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Cancel a reminder by ID: /cancel <id>
        """
        try:
            if not context.args:
                await update.message.reply_text("Usage: /cancel <reminder_id>")
                return
            try:
                reminder_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("Reminder ID must be a number.")
                return
            if not self.db:
                self.db = DatabaseManager()
            if not self.scheduler_manager:
                self.scheduler_manager = SchedulerManager(self.db)
                self.scheduler_manager.start()
            result = self.scheduler_manager.cancel_reminder(reminder_id)
            if result.get('success'):
                await update.message.reply_text(f"✅ Cancelled reminder #{reminder_id}")
            else:
                await update.message.reply_text(f"❌ Could not cancel: {result.get('error','unknown error')}")
        except Exception as e:
            logger.error(f"/cancel error: {e}")
            await update.message.reply_text("Sorry, I couldn't cancel that reminder.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /status command - show bot status.
        """
        try:
            # Check if assistant is working
            test_response = self.assistant.process_text_message("Hello")
            
            status_message = """
✅ **Jarvis Status: ONLINE**

🧠 AI Assistant: Active
🎤 Voice Recognition: Ready
🔊 Text-to-Speech: Ready
📚 Knowledge Base: Ready
🔗 Telegram Integration: Connected

All systems operational! 🚀
            """
            
        except Exception as e:
            status_message = f"""
❌ **Jarvis Status: ERROR**

There seems to be an issue with my systems:
{str(e)}

Please check the configuration and try again.
            """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def voice_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Enable voice responses.
        """
        context.user_data['voice_enabled'] = True
        await update.message.reply_text("🔊 Voice responses enabled! I'll now reply with audio when possible.")
    
    async def voice_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Disable voice responses.
        """
        context.user_data['voice_enabled'] = False
        await update.message.reply_text("🔇 Voice responses disabled. I'll reply with text only.")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming text messages.
        """
        try:
            user_message = update.message.text
            user_id = update.effective_user.id
            
            # Check for YouTube links with regex to include all variants
            import re
            youtube_patterns = [r'youtube\.com', r'youtu\.be', r'm\.youtube\.com']
            if any(re.search(pattern, user_message, re.IGNORECASE) for pattern in youtube_patterns):
                from core.youtube_utils import YouTubeDownloader
                downloader = YouTubeDownloader()
                
                # Show downloading indicator
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_video")
                
                # Extract URL from message
                url_match = re.search(r'https?://\S+', user_message)
                if not url_match:
                    await update.message.reply_text("I couldn't find a valid YouTube URL in your message.")
                    return
                
                url = url_match.group(0)
                logger.info(f"Detected YouTube URL: {url}")
                
                # Download video at 240p to reduce file size for messaging platforms
                file_path, error = downloader.download_video(url, quality='240p')
                
                if file_path:
                    try:
                        with open(file_path, 'rb') as video_file:
                            await update.message.reply_video(video_file, caption="Downloaded from YouTube")
                    except Exception as e:
                        logger.error(f"Error sending video: {e}")
                        await update.message.reply_text(f"Error sending video: {str(e)}")
                    finally:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as cleanup_err:
                            logger.warning(f"Cleanup failed for {file_path}: {cleanup_err}")
                    return
                else:
                    await update.message.reply_text(f"Failed to download video: {error}")
                    return
            
            # Instagram/TikTok detection and download
            ig_tt_patterns = [r'instagram\.com', r'instagr\.am', r'tiktok\.com', r'vm\.tiktok\.com']
            if any(re.search(pattern, user_message, re.IGNORECASE) for pattern in ig_tt_patterns):
                from core.youtube_utils import YouTubeDownloader
                downloader = YouTubeDownloader()
                
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_video")
                url_match = re.search(r'https?://\S+', user_message)
                if not url_match:
                    await update.message.reply_text("I couldn't find a valid Instagram/TikTok URL in your message.")
                    return
                url = url_match.group(0)
                logger.info(f"Detected IG/TikTok URL: {url}")
                
                file_path, error = downloader.download_video(url, quality='240p')
                if file_path:
                    try:
                        with open(file_path, 'rb') as video_file:
                            await update.message.reply_video(video_file, caption="Downloaded video")
                    except Exception as e:
                        logger.error(f"Error sending video: {e}")
                        await update.message.reply_text(f"Error sending video: {str(e)}")
                    finally:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception as cleanup_err:
                            logger.warning(f"Cleanup failed for {file_path}: {cleanup_err}")
                    return
                else:
                    await update.message.reply_text(f"Failed to download video: {error}")
                    return
            
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Process message with assistant
            # Natural-language reminders: today/tomorrow by HH:MM(am/pm) or explicit date
            try:
                m1 = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(today|tomorrow)\s+at\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)', user_message, re.IGNORECASE)
                m2 = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(\d{1,2}:\d{2}\s*(?:am|pm)?)\b', user_message, re.IGNORECASE)
                m3 = re.search(r'remind me to\s+(.+?)\s+(?:by|at)\s+(\d{4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2})', user_message, re.IGNORECASE)
                time_tuple = None
                title = None
                if m1:
                    title = m1.group(1).strip()
                    time_tuple = (m1.group(2).lower(), m1.group(3).strip())
                elif m2:
                    title = m2.group(1).strip()
                    time_tuple = (None, m2.group(2).strip())
                elif m3:
                    title = m3.group(1).strip()
                    time_tuple = (m3.group(2).strip(), m3.group(3).strip())
                if time_tuple and self.scheduler_manager and self.db:
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
                    dt = to_datetime(time_tuple)
                    chat_id = str(update.effective_chat.id)
                    tg_user = update.effective_user
                    user = self.db.get_or_create_user(
                        platform_id=chat_id,
                        platform='telegram',
                        username=getattr(tg_user, 'username', None),
                        first_name=getattr(tg_user, 'first_name', None),
                        last_name=getattr(tg_user, 'last_name', None)
                    )
                    result = self.scheduler_manager.create_reminder({
                        'user_id': user['id'],
                        'title': title,
                        'description': '',
                        'reminder_time': dt.isoformat(),
                        'repeat_pattern': None
                    })
                    if result.get('success'):
                        await update.message.reply_text(f"✅ Reminder set for {result['scheduled_time']}\nTitle: {title}")
                    else:
                        await update.message.reply_text(f"❌ Could not create reminder: {result.get('error','unknown error')}")
                    return
            except Exception as e:
                logger.error(f"Reminder parse error: {e}")
            
            response = self.assistant.process_text_message(user_message)
            
            # Send text response
            await update.message.reply_text(response)
            
            # Send voice response if enabled
            if context.user_data.get('voice_enabled', False):
                await self._send_voice_response(update, context, response)
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text(
                "I apologize, but I encountered an error processing your message. Please try again."
            )
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming voice messages.
        """
        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Download voice message
            voice_file = await update.message.voice.get_file()
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
                await voice_file.download_to_drive(temp_audio.name)
                
                # Process voice message
                transcribed_text, ai_response = self.assistant.process_voice_message(temp_audio.name)
                
                # Clean up temporary file
                os.unlink(temp_audio.name)
            
            # Send transcription and response
            if transcribed_text and transcribed_text != "Could not understand the audio.":
                await update.message.reply_text(f"🎤 You said: \"{transcribed_text}\"")
            
            await update.message.reply_text(ai_response)
            
            # Send voice response if enabled
            if context.user_data.get('voice_enabled', False):
                await self._send_voice_response(update, context, ai_response)
                
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            await update.message.reply_text(
                "I had trouble processing your voice message. Please try again or send a text message."
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming document files (PDFs).
        """
        try:
            document = update.message.document
            
            # Check if it's a PDF
            if not document.file_name.lower().endswith('.pdf'):
                await update.message.reply_text(
                    "I can only process PDF documents at the moment. Please send a PDF file."
                )
                return
            
            # Show upload indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
            
            # Download document
            doc_file = await document.get_file()
            
            # Download into project documents directory to avoid temp file locks
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'documents', 'telegram_uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            safe_name = document.file_name or 'upload.pdf'
            base, ext = os.path.splitext(safe_name)
            if not ext.lower() == '.pdf':
                ext = '.pdf'
            local_path = os.path.join(uploads_dir, f"{int(time.time()*1000)}_{base}{ext}")
            try:
                await doc_file.download_to_drive(local_path)
                # Summarize PDF
                summary = self.assistant.summarize_pdf(local_path)
            finally:
                # Best-effort cleanup, ignore failures
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                except Exception:
                    pass
            
            # Reply with summary
            await update.message.reply_text(
                f"📄 Summary of {document.file_name}:\n\n{summary}"
            )
            
        except Exception as e:
            logger.error(f"Error handling document: {e}")
            await update.message.reply_text(
                "I encountered an error while processing your document. Please try again."
            )

    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Generate an image from a text prompt and send it.
        Usage: /image your prompt here
        """
        try:
            prompt = ' '.join(context.args).strip() if context.args else ''
            if not prompt:
                await update.message.reply_text("Usage: /image your prompt here")
                return
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
            waiting = await update.message.reply_text("🎨 Generating image... This may take ~10–20s")
            img_path = self.assistant.generate_image_file(prompt)
            if img_path and os.path.exists(img_path):
                with open(img_path, 'rb') as img:
                    await update.message.reply_photo(img, caption=f"Image: {prompt}")
                try:
                    os.remove(img_path)
                except Exception:
                    pass
            else:
                await update.message.reply_text("Sorry, I couldn't generate an image right now.")
            try:
                await waiting.delete()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            await update.message.reply_text("An error occurred while generating the image.")

    async def email_summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Summarize recent inbox emails.
        Usage: /email_summary [count]
        """
        try:
            count = 5
            if context.args:
                try:
                    count = max(1, min(20, int(context.args[0])))
                except Exception:
                    pass
            if not self.email_agent:
                self.email_agent = EmailAgent()
            await update.message.reply_text("📬 Fetching recent emails...")
            emails = self.email_agent.fetch_recent_emails(limit=count)
            summary = self.email_agent.summarize_emails(emails)
            await update.message.reply_text(summary)
        except Exception as e:
            logger.error(f"/email_summary error: {e}")
            await update.message.reply_text("I couldn't summarize your inbox. Check IMAP settings.")

    async def email_draft_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Draft a reply from pasted email context and brief instructions.
        Usage: /email_draft <instructions> (reply to a message containing the email text, or paste it)
        """
        try:
            instructions = ' '.join(context.args).strip() if context.args else ''
            if not instructions:
                await update.message.reply_text("Usage: /email_draft <instructions>. Reply to an email text or paste it below.")
                return
            # Try to get email context from replied message
            email_context = ''
            if update.message and update.message.reply_to_message and update.message.reply_to_message.text:
                email_context = update.message.reply_to_message.text
            else:
                await update.message.reply_text("Please reply to a message containing the email content to draft a reply.")
                return
            if not self.email_agent:
                self.email_agent = EmailAgent()
            draft = self.email_agent.draft_reply(email_context, instructions)
            await update.message.reply_text(f"✉️ Draft reply:\n\n{draft}")
        except Exception as e:
            logger.error(f"/email_draft error: {e}")
            await update.message.reply_text("I couldn't draft a reply right now.")
    
    async def _send_voice_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        """
        Send voice response if voice is enabled.
        """
        try:
            # Show record audio indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
            
            # Generate voice response
            voice_file_path = self.assistant.generate_voice_response(text)
            
            if voice_file_path and os.path.exists(voice_file_path):
                # Send voice message
                with open(voice_file_path, 'rb') as voice_file:
                    await context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=voice_file
                    )
                
                # Clean up voice file
                os.unlink(voice_file_path)
                
        except Exception as e:
            logger.error(f"Error sending voice response: {e}")
            # Silently fail for voice responses
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle errors in the bot.
        """
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "I encountered an unexpected error. Please try again or contact support if the issue persists."
            )
    
    def setup_handlers(self) -> None:
        """
        Set up all message and command handlers.
        """
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("reminders", self.reminders_command))
        self.application.add_handler(CommandHandler("cancel", self.cancel_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("voice_on", self.voice_on_command))
        self.application.add_handler(CommandHandler("voice_off", self.voice_off_command))
        self.application.add_handler(CommandHandler("image", self.image_command))
        self.application.add_handler(CommandHandler("email_summary", self.email_summary_command))
        self.application.add_handler(CommandHandler("email_draft", self.email_draft_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        self.application.add_handler(MessageHandler(filters.Document.PDF, self.handle_document))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    def run(self) -> None:
        """
        Start the Telegram bot.
        """
        try:
            # Create application with better connection settings
            self.application = (
                Application.builder()
                .token(self.token)
                .connect_timeout(300.0)
                .read_timeout(300.0)
                .write_timeout(300.0)
                .pool_timeout(300.0)
                .build()
            )
            
            # Start scheduler so reminders fire
            try:
                self.db = DatabaseManager()
                self.scheduler_manager = SchedulerManager(self.db)
                self.scheduler_manager.start()
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
            
            # Setup handlers
            self.setup_handlers()
            
            logger.info("Starting Jarvis Telegram Bot...")
            
            # Start the bot with polling settings
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                timeout=30,
                bootstrap_retries=3,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

def run_telegram_bot():
    """
    Main function to run the Telegram bot.
    """
    try:
        # Test token first
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return
        
        # Quick token validation
        import requests
        test_url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            response = requests.get(test_url, timeout=10)
            if response.status_code != 200:
                logger.error(f"Invalid Telegram bot token. Status: {response.status_code}")
                return
            logger.info("Telegram bot token validated successfully")
        except requests.RequestException as e:
            logger.error(f"Could not validate token: {e}")
            return
        
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    run_telegram_bot()
