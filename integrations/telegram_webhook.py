import os
import logging
import requests
import json
from typing import Dict, Any, Optional
import tempfile
from dotenv import load_dotenv
import re
YouTubeDownloader = None
try:
    from core.youtube_utils import YouTubeDownloader as _YTD
    YouTubeDownloader = _YTD
except Exception:
    YouTubeDownloader = None

load_dotenv()
logger = logging.getLogger(__name__)

class TelegramWebhook:
    """
    Telegram Bot API webhook integration.
    Handles webhook processing and message routing.
    """
    
    def __init__(self, message_router):
        self.message_router = message_router
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        self.api_base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        logger.info("Telegram webhook integration initialized")
    
    def handle_update(self, update_data: Dict) -> Dict:
        """
        Handle incoming Telegram webhook update.
        
        Args:
            update_data (Dict): Webhook payload
            
        Returns:
            Dict: Processing result
        """
        try:
            if 'message' in update_data:
                self._process_message(update_data['message'])
            elif 'edited_message' in update_data:
                self._process_message(update_data['edited_message'])
            elif 'callback_query' in update_data:
                self._process_callback_query(update_data['callback_query'])
            
            return {'status': 'processed'}
            
        except Exception as e:
            logger.error(f"Error handling Telegram update: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _process_message(self, message: Dict) -> None:
        """Process individual Telegram message."""
        try:
            user = message.get('from', {})
            chat = message.get('chat', {})
            user_id = str(user.get('id'))
            
            # Extract message content
            message_data = self._extract_message_content(message)
            
            if not message_data:
                logger.warning(f"Could not extract content from message: {message}")
                return
            
            # Add user info
            message_data['user_info'] = {
                'username': user.get('username'),
                'first_name': user.get('first_name'),
                'last_name': user.get('last_name')
            }

            # Check for YouTube links
            if message_data['type'] == 'text':
                text = message_data['content']
                youtube_patterns = [r'youtube\\.com', r'youtu\\.be', r'm\\.youtube\\.com']
                if any(re.search(pattern, text, re.IGNORECASE) for pattern in youtube_patterns):
                    try:
                        # Extract URL
                        url_match = re.search(r'https?://\\S+', text)
                        if url_match:
                            url = url_match.group(0)
                            if YouTubeDownloader is None:
                                self._send_text_message(chat['id'], "Video download isn't enabled on this server.")
                                return
                            downloader = YouTubeDownloader()
                            video_path = downloader.download_video(url)
                            
                            if video_path:
                                success = self._send_video_message(chat['id'], video_path, "Downloaded YouTube video")
                                if success:
                                    os.remove(video_path)
                                else:
                                    os.remove(video_path)
                                    self._send_text_message(chat['id'], "Failed to send the video.")
                            else:
                                self._send_text_message(chat['id'], "Failed to download the video.")
                        else:
                            self._send_text_message(chat['id'], "No valid URL found in the message.")
                        
                        return  # Don't process further
                        
                    except Exception as e:
                        logger.error(f"Error handling YouTube link: {e}")
                        self._send_text_message(chat['id'], f"Error downloading video: {str(e)}")
                        return
            
            # Process through message router
            response = self.message_router.process_message(
                platform='telegram',
                platform_user_id=user_id,
                message_data=message_data
            )
            # Send response back to Telegram
            if response.get('success', True):
                self._send_response(chat['id'], response)
        
        except Exception as e:
            logger.error(f"Error processing Telegram message: {e}")
    
    def _extract_message_content(self, message: Dict) -> Optional[Dict]:
        """Extract content from Telegram message based on type."""
        
        if 'text' in message:
            return {
                'type': 'text',
                'content': message['text']
            }
        
        elif 'voice' in message:
            voice_info = message['voice']
            return {
                'type': 'voice',
                'content': 'Voice message',
                'file_info': {
                    'file_id': voice_info.get('file_id'),
                    'file_unique_id': voice_info.get('file_unique_id'),
                    'duration': voice_info.get('duration'),
                    'mime_type': voice_info.get('mime_type'),
                    'file_size': voice_info.get('file_size')
                }
            }
        
        elif 'document' in message:
            doc_info = message['document']
            return {
                'type': 'document',
                'content': 'Document',
                'file_info': {
                    'file_id': doc_info.get('file_id'),
                    'file_unique_id': doc_info.get('file_unique_id'),
                    'filename': doc_info.get('file_name'),
                    'mime_type': doc_info.get('mime_type'),
                    'file_size': doc_info.get('file_size')
                }
            }
        
        elif 'photo' in message:
            # Get the largest photo
            photos = message['photo']
            largest_photo = max(photos, key=lambda x: x.get('file_size', 0))
            
            return {
                'type': 'image',
                'content': message.get('caption', 'Image'),
                'file_info': {
                    'file_id': largest_photo.get('file_id'),
                    'file_unique_id': largest_photo.get('file_unique_id'),
                    'width': largest_photo.get('width'),
                    'height': largest_photo.get('height'),
                    'file_size': largest_photo.get('file_size')
                }
            }
        
        elif 'video' in message:
            video_info = message['video']
            return {
                'type': 'video',
                'content': message.get('caption', 'Video'),
                'file_info': {
                    'file_id': video_info.get('file_id'),
                    'file_unique_id': video_info.get('file_unique_id'),
                    'width': video_info.get('width'),
                    'height': video_info.get('height'),
                    'duration': video_info.get('duration'),
                    'mime_type': video_info.get('mime_type'),
                    'file_size': video_info.get('file_size')
                }
            }
        
        else:
            logger.warning(f"Unsupported message type in: {list(message.keys())}")
            return None
    
    def _send_response(self, chat_id: int, response: Dict) -> bool:
        """Send response back to Telegram user."""
        try:
            response_type = response.get('type', 'text')
            content = response.get('content', '')
            
            if response_type == 'text':
                return self._send_text_message(chat_id, content)
            
            elif response_type == 'image' and response.get('image_url'):
                return self._send_photo_message(chat_id, response['image_url'], content)
            
            else:
                # Fallback to text
                return self._send_text_message(chat_id, content)
                
        except Exception as e:
            logger.error(f"Error sending Telegram response: {e}")
            return False
    
    def _send_text_message(self, chat_id: int, text: str) -> bool:
        """Send text message via Telegram API."""
        try:
            url = f"{self.api_base_url}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            return False
    
    def _send_photo_message(self, chat_id: int, photo_url: str, caption: str = "") -> bool:
        """Send photo message via Telegram API."""
        try:
            url = f"{self.api_base_url}/sendPhoto"
            
            payload = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Photo sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send photo: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending photo message: {e}")
            return False
    
    def _send_video_message(self, chat_id: int, video_path: str, caption: str = "") -> bool:
        """Send video message via Telegram API."""
        try:
            url = f"{self.api_base_url}/sendVideo"
            
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                data = {
                    'chat_id': str(chat_id),
                    'caption': caption
                }
                response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                logger.info(f"Video sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send video: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending video message: {e}")
            return False
    
    def _download_file(self, file_id: str) -> Optional[str]:
        """Download file from Telegram."""
        try:
            # Get file info
            url = f"{self.api_base_url}/getFile"
            response = requests.get(url, params={"file_id": file_id})
            
            if response.status_code != 200:
                logger.error(f"Failed to get file info: {response.text}")
                return None
            
            file_path = response.json().get('result', {}).get('file_path')
            if not file_path:
                logger.error("No file path in response")
                return None
            
            # Download the actual file
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            file_response = requests.get(file_url)
            
            if file_response.status_code != 200:
                logger.error(f"Failed to download file: {file_response.status_code}")
                return None
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_response.content)
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def _process_callback_query(self, callback_query: Dict) -> None:
        """Process callback query from inline keyboards."""
        try:
            query_id = callback_query.get('id')
            data = callback_query.get('data')
            user = callback_query.get('from', {})
            
            # Answer callback query
            self._answer_callback_query(query_id, "Processing...")
            
            # Process the callback data
            # This could be extended for interactive features
            
        except Exception as e:
            logger.error(f"Error processing callback query: {e}")
    
    def _answer_callback_query(self, query_id: str, text: str = "") -> bool:
        """Answer callback query."""
        try:
            url = f"{self.api_base_url}/answerCallbackQuery"
            payload = {
                "callback_query_id": query_id,
                "text": text
            }
            
            response = requests.post(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    def send_message(self, chat_id: int, message: str) -> bool:
        """
        Public method to send message to Telegram user.
        
        Args:
            chat_id (int): Chat ID
            message (str): Message content
            
        Returns:
            bool: Success status
        """
        return self._send_text_message(chat_id, message)
