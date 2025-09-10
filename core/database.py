import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    SQLite database manager for Jarvis bot.
    Handles all database operations including users, conversations, documents, and reminders.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'jarvis.db')
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._initialize_database()
        logger.info(f"Database initialized at {db_path}")
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform_id TEXT UNIQUE NOT NULL,
                    platform TEXT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    preferences TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL,
                    user_message TEXT,
                    bot_response TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Documents table (knowledge base)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    content_summary TEXT,
                    embeddings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Reminders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    reminder_time TIMESTAMP NOT NULL,
                    repeat_pattern TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_completed BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Sessions table (for context management)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_data TEXT DEFAULT '{}',
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    user_id INTEGER,
                    event_data TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def get_or_create_user(self, platform_id: str, platform: str, **kwargs) -> Dict:
        """Get existing user or create new one."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Try to get existing user
            cursor.execute(
                'SELECT * FROM users WHERE platform_id = ? AND platform = ?',
                (platform_id, platform)
            )
            user = cursor.fetchone()
            
            if user:
                # Update last_active
                cursor.execute(
                    'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?',
                    (user['id'],)
                )
                conn.commit()
                return dict(user)
            else:
                # Create new user
                cursor.execute('''
                    INSERT INTO users (platform_id, platform, username, first_name, last_name, preferences)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    platform_id,
                    platform,
                    kwargs.get('username'),
                    kwargs.get('first_name'),
                    kwargs.get('last_name'),
                    json.dumps(kwargs.get('preferences', {}))
                ))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                # Return new user
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                return dict(cursor.fetchone())
    
    def save_conversation(self, user_id: int, message_type: str, user_message: str, 
                         bot_response: str, metadata: Dict = None) -> int:
        """Save conversation to database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversations (user_id, message_type, user_message, bot_response, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                message_type,
                user_message,
                bot_response,
                json.dumps(metadata or {})
            ))
            
            conversation_id = cursor.lastrowid
            conn.commit()
            return conversation_id
    
    def get_conversations(self, user_id: int = None, limit: int = 50) -> List[Dict]:
        """Get conversation history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT * FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (user_id, limit))
            else:
                cursor.execute('''
                    SELECT c.*, u.username, u.platform 
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    ORDER BY c.created_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def save_document(self, user_id: int, filename: str, file_path: str, 
                     file_type: str, file_size: int, content_summary: str = None,
                     embeddings: str = None) -> int:
        """Save document metadata to database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO documents (user_id, filename, file_path, file_type, 
                                     file_size, content_summary, embeddings)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, filename, file_path, file_type, 
                file_size, content_summary, embeddings
            ))
            
            doc_id = cursor.lastrowid
            conn.commit()
            return doc_id
    
    def get_user_documents(self, user_id: int) -> List[Dict]:
        """Get all documents for a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM documents 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            ''', (user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_reminder(self, user_id: int, title: str, description: str,
                       reminder_time: datetime, repeat_pattern: str = None) -> int:
        """Create a new reminder."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO reminders (user_id, title, description, reminder_time, repeat_pattern)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, title, description, reminder_time, repeat_pattern))
            
            reminder_id = cursor.lastrowid
            conn.commit()
            return reminder_id
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get all pending reminders."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT r.*, u.platform_id, u.platform 
                FROM reminders r
                JOIN users u ON r.user_id = u.id
                WHERE r.is_active = 1 
                AND r.is_completed = 0 
                AND r.reminder_time <= CURRENT_TIMESTAMP
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def complete_reminder(self, reminder_id: int):
        """Mark reminder as completed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE reminders 
                SET is_completed = 1 
                WHERE id = ?
            ''', (reminder_id,))
            
            conn.commit()
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT preferences FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result:
                return json.loads(result['preferences'])
            return {}
    
    def update_user_preferences(self, user_id: int, preferences: Dict):
        """Update user preferences."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET preferences = ? 
                WHERE id = ?
            ''', (json.dumps(preferences), user_id))
            
            conn.commit()
    
    def log_analytics_event(self, event_type: str, user_id: int = None, event_data: Dict = None):
        """Log analytics event."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analytics (event_type, user_id, event_data)
                VALUES (?, ?, ?)
            ''', (event_type, user_id, json.dumps(event_data or {})))
            
            conn.commit()
    
    def get_user_count(self) -> int:
        """Get total user count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM users')
            return cursor.fetchone()['count']
    
    def get_message_count(self) -> int:
        """Get total message count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM conversations')
            return cursor.fetchone()['count']
    
    def get_document_count(self) -> int:
        """Get total document count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM documents')
            return cursor.fetchone()['count']
    
    def cleanup_old_sessions(self, days: int = 7):
        """Clean up old sessions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute('''
                DELETE FROM sessions 
                WHERE expires_at < ? OR created_at < ?
            ''', (cutoff_date, cutoff_date))
            
            conn.commit()
    
    def health_check(self) -> bool:
        """Check database health."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_user_reminders(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Get reminders for a specific user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM reminders 
                WHERE user_id = ?
            '''
            params = [user_id]
            
            if active_only:
                query += ' AND is_active = 1 AND is_completed = 0'
            
            query += ' ORDER BY reminder_time ASC'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
