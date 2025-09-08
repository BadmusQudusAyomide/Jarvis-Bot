import os
import logging
import requests
import json
from typing import Dict, Any, Optional
from flask import request, jsonify
import tempfile
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class WhatsAppWebhook:
    """
    WhatsApp Business API integration using existing access token.
    Handles webhook verification and message processing.
    """
    
    def __init__(self, message_router):
        self.message_router = message_router
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.webhook_verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
        
        if not all([self.access_token, self.phone_number_id, self.webhook_verify_token]):
            raise ValueError("Missing WhatsApp configuration in environment variables")
        
        self.api_base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        logger.info("WhatsApp webhook integration initialized")
    
    def verify_webhook(self, request_obj) -> Any:
        """
        Verify webhook for WhatsApp Business API.
        
        Args:
            request_obj: Flask request object
            
        Returns:
            Verification response
        """
        try:
            mode = request_obj.args.get('hub.mode')
            token = request_obj.args.get('hub.verify_token')
            challenge = request_obj.args.get('hub.challenge')
            
            if mode and token:
                if mode == 'subscribe' and token == self.webhook_verify_token:
                    logger.info("WhatsApp webhook verified successfully")
                    return challenge
                else:
                    logger.warning("WhatsApp webhook verification failed")
                    return jsonify({'error': 'Verification failed'}), 403
            
            return jsonify({'error': 'Missing parameters'}), 400
            
        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return jsonify({'error': str(e)}), 500
    
    def handle_update(self, update_data: Dict) -> Dict:
        """
        Handle incoming WhatsApp webhook update.
        
        Args:
            update_data (Dict): Webhook payload
            
        Returns:
            Dict: Processing result
        """
        try:
            if not update_data.get('entry'):
                return {'status': 'no_entry'}
            
            for entry in update_data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if change.get('field') == 'messages':
                            value = change.get('value', {})
                            
                            # Process messages
                            if 'messages' in value:
                                for message in value['messages']:
                                    self._process_message(message, value)
                            
                            # Process status updates
                            if 'statuses' in value:
                                for status in value['statuses']:
                                    self._process_status_update(status)
            
            return {'status': 'processed'}
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp update: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _process_message(self, message: Dict, value: Dict) -> None:
        """Process individual WhatsApp message."""
        try:
            from_number = message.get('from')
            message_id = message.get('id')
            timestamp = message.get('timestamp')
            
            # Extract message content based on type
            message_data = self._extract_message_content(message)
            
            if not message_data:
                logger.warning(f"Could not extract content from message: {message}")
                return
            
            # Add user info
            contacts = value.get('contacts', [])
            user_info = {}
            for contact in contacts:
                if contact.get('wa_id') == from_number:
                    profile = contact.get('profile', {})
                    user_info = {
                        'first_name': profile.get('name', ''),
                        'username': from_number
                    }
                    break
            
            message_data['user_info'] = user_info
            
            # Process through message router
            response = self.message_router.process_message(
                platform='whatsapp',
                platform_user_id=from_number,
                message_data=message_data
            )
            
            # Send response back to WhatsApp
            if response.get('success', True):
                self._send_response(from_number, response)
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {e}")
    
    def _extract_message_content(self, message: Dict) -> Optional[Dict]:
        """Extract content from WhatsApp message based on type."""
        message_type = message.get('type')
        
        if message_type == 'text':
            return {
                'type': 'text',
                'content': message.get('text', {}).get('body', '')
            }
        
        elif message_type == 'audio':
            audio_info = message.get('audio', {})
            return {
                'type': 'voice',
                'content': 'Voice message',
                'file_info': {
                    'id': audio_info.get('id'),
                    'mime_type': audio_info.get('mime_type'),
                    'file_size': audio_info.get('file_size')
                }
            }
        
        elif message_type == 'document':
            doc_info = message.get('document', {})
            return {
                'type': 'document',
                'content': 'Document',
                'file_info': {
                    'id': doc_info.get('id'),
                    'filename': doc_info.get('filename'),
                    'mime_type': doc_info.get('mime_type'),
                    'file_size': doc_info.get('file_size')
                }
            }
        
        elif message_type == 'image':
            image_info = message.get('image', {})
            return {
                'type': 'image',
                'content': 'Image',
                'file_info': {
                    'id': image_info.get('id'),
                    'mime_type': image_info.get('mime_type'),
                    'file_size': image_info.get('file_size'),
                    'caption': image_info.get('caption', '')
                }
            }
        
        elif message_type == 'video':
            video_info = message.get('video', {})
            return {
                'type': 'video',
                'content': 'Video',
                'file_info': {
                    'id': video_info.get('id'),
                    'mime_type': video_info.get('mime_type'),
                    'file_size': video_info.get('file_size'),
                    'caption': video_info.get('caption', '')
                }
            }
        
        else:
            logger.warning(f"Unsupported message type: {message_type}")
            return None
    
    def _send_response(self, to_number: str, response: Dict) -> bool:
        """Send response back to WhatsApp user."""
        try:
            response_type = response.get('type', 'text')
            content = response.get('content', '')
            
            if response_type == 'text':
                return self._send_text_message(to_number, content)
            
            elif response_type == 'image' and response.get('image_url'):
                return self._send_image_message(to_number, response['image_url'], content)
            
            else:
                # Fallback to text
                return self._send_text_message(to_number, content)
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp response: {e}")
            return False
    
    def _send_text_message(self, to_number: str, text: str) -> bool:
        """Send text message via WhatsApp API."""
        try:
            url = f"{self.api_base_url}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {
                    "body": text
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {to_number}")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            return False
    
    def _send_image_message(self, to_number: str, image_url: str, caption: str = "") -> bool:
        """Send image message via WhatsApp API."""
        try:
            url = f"{self.api_base_url}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "image",
                "image": {
                    "link": image_url,
                    "caption": caption
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Image sent successfully to {to_number}")
                return True
            else:
                logger.error(f"Failed to send image: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending image message: {e}")
            return False
    
    def _download_media_file(self, media_id: str) -> Optional[str]:
        """Download media file from WhatsApp."""
        try:
            # Get media URL
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get media URL: {response.text}")
                return None
            
            media_url = response.json().get('url')
            if not media_url:
                logger.error("No media URL in response")
                return None
            
            # Download the actual file
            file_response = requests.get(media_url, headers=headers)
            if file_response.status_code != 200:
                logger.error(f"Failed to download media file: {file_response.status_code}")
                return None
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_response.content)
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading media file: {e}")
            return None
    
    def _process_status_update(self, status: Dict) -> None:
        """Process message status updates (delivered, read, etc.)."""
        try:
            message_id = status.get('id')
            recipient_id = status.get('recipient_id')
            status_type = status.get('status')
            timestamp = status.get('timestamp')
            
            logger.info(f"Message {message_id} to {recipient_id}: {status_type}")
            
            # Could store delivery status in database here
            
        except Exception as e:
            logger.error(f"Error processing status update: {e}")
    
    def send_message(self, to_number: str, message: str) -> bool:
        """
        Public method to send message to WhatsApp user.
        
        Args:
            to_number (str): Recipient phone number
            message (str): Message content
            
        Returns:
            bool: Success status
        """
        return self._send_text_message(to_number, message)
