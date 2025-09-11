from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from datetime import datetime
import json
from dotenv import load_dotenv
import threading

# Import core modules
from core.database import DatabaseManager
from core.ai_engine import AIEngine
from core.message_router import MessageRouter
from integrations.telegram_webhook import TelegramWebhook
from integrations.whatsapp_webhook import WhatsAppWebhook
from core.scheduler import SchedulerManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jarvis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class JarvisApp:
    """
    Main Jarvis application with Flask web framework.
    Handles all messaging platforms through webhooks.
    """
    
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize core components
        self.db = DatabaseManager()
        self.ai_engine = AIEngine()
        self.message_router = MessageRouter(self.db, self.ai_engine, self.scheduler)
        self.scheduler = SchedulerManager(self.db)
        
        # Initialize integrations
        self.telegram = TelegramWebhook(self.message_router)
        self.whatsapp = WhatsAppWebhook(self.message_router)
        
        # Setup routes
        self._setup_routes()
        
        # Start scheduler
        self.scheduler.start()
        
        logger.info("Jarvis application initialized successfully")
    
    def _setup_routes(self):
        """Setup Flask routes for webhooks and API endpoints."""
        
        @self.app.route('/', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '2.0.0',
                'services': {
                    'database': self.db.health_check(),
                    'ai_engine': self.ai_engine.health_check(),
                    'scheduler': self.scheduler.is_running()
                }
            })
        
        @self.app.route('/webhook/telegram', methods=['POST'])
        def telegram_webhook():
            """Handle Telegram webhook."""
            try:
                update_data = request.get_json()
                if update_data:
                    threading.Thread(target=self.telegram.handle_update, args=(update_data,)).start()
                return jsonify({'status': 'ok'})
            except Exception as e:
                logger.error(f"Telegram webhook error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/webhook/whatsapp', methods=['GET', 'POST'])
        def whatsapp_webhook():
            """Handle WhatsApp webhook (Twilio)."""
            try:
                if request.method == 'GET':
                    # Webhook verification
                    return self.whatsapp.verify_webhook(request)
                else:
                    update_data = request.get_json()
                    threading.Thread(target=self.whatsapp.handle_update, args=(update_data,)).start()
                    return jsonify({'status': 'ok'})
            except Exception as e:
                logger.error(f"WhatsApp webhook error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/conversations', methods=['GET'])
        def get_conversations():
            """Get user conversations."""
            try:
                user_id = request.args.get('user_id')
                limit = int(request.args.get('limit', 50))
                conversations = self.db.get_conversations(user_id, limit)
                return jsonify(conversations)
            except Exception as e:
                logger.error(f"API error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/knowledge-base', methods=['POST'])
        def upload_document():
            """Upload document to knowledge base."""
            try:
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                user_id = request.form.get('user_id')
                
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                # Process document
                result = self.ai_engine.add_document(file, user_id)
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Document upload error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/reminders', methods=['GET', 'POST'])
        def handle_reminders():
            """Handle reminder operations."""
            try:
                if request.method == 'GET':
                    user_id = request.args.get('user_id')
                    reminders = self.scheduler.get_user_reminders(user_id)
                    return jsonify(reminders)
                else:
                    data = request.get_json()
                    result = self.scheduler.create_reminder(data)
                    return jsonify(result)
            except Exception as e:
                logger.error(f"Reminders API error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            """Get application statistics."""
            try:
                stats = {
                    'total_users': self.db.get_user_count(),
                    'total_messages': self.db.get_message_count(),
                    'active_reminders': self.scheduler.get_active_reminder_count(),
                    'knowledge_base_docs': self.db.get_document_count(),
                    'uptime': self.scheduler.get_uptime()
                }
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Stats API error: {e}")
                return jsonify({'error': str(e)}), 500
    
    def run(self, host='0.0.0.0', port=None, debug=False):
        """Run the Flask application."""
        if port is None:
            port = int(os.getenv('PORT', 5000))
        
        logger.info(f"Starting Jarvis server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_app():
    """Factory function to create Flask app instance"""
    app_instance = JarvisApp()
    return app_instance.app

if __name__ == '__main__':
    app = JarvisApp()
    port = int(os.getenv('PORT', 5000))
    app.app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG_MODE', 'False').lower() == 'true')
