import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import json

logger = logging.getLogger(__name__)

class SchedulerManager:
    """
    Advanced scheduler for reminders, tasks, and automation using APScheduler.
    """
    
    def __init__(self, database_manager):
        self.db = database_manager
        
        # Configure job stores
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        
        self.start_time = datetime.now()
        
        logger.info("Scheduler manager initialized")
    
    def start(self):
        """Start the scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
                
                # Schedule periodic cleanup
                self.scheduler.add_job(
                    func=self._cleanup_completed_reminders,
                    trigger=IntervalTrigger(hours=24),
                    id='cleanup_reminders',
                    replace_existing=True
                )
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    def stop(self):
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def create_reminder(self, reminder_data: Dict) -> Dict:
        """
        Create a new reminder.
        
        Args:
            reminder_data (Dict): Reminder information
            
        Returns:
            Dict: Creation result
        """
        try:
            user_id = reminder_data.get('user_id')
            title = reminder_data.get('title')
            description = reminder_data.get('description', '')
            reminder_time_str = reminder_data.get('reminder_time')
            repeat_pattern = reminder_data.get('repeat_pattern')
            
            if not all([user_id, title, reminder_time_str]):
                return {'success': False, 'error': 'Missing required fields'}
            
            # Parse reminder time
            try:
                if isinstance(reminder_time_str, str):
                    reminder_time = datetime.fromisoformat(reminder_time_str)
                else:
                    reminder_time = reminder_time_str
            except ValueError:
                return {'success': False, 'error': 'Invalid datetime format'}
            
            # Create reminder in database
            reminder_id = self.db.create_reminder(
                user_id=user_id,
                title=title,
                description=description,
                reminder_time=reminder_time,
                repeat_pattern=repeat_pattern
            )
            
            # Schedule the job
            job_id = f"reminder_{reminder_id}"
            
            if repeat_pattern:
                trigger = self._create_repeat_trigger(repeat_pattern, reminder_time)
            else:
                trigger = DateTrigger(run_date=reminder_time)
            
            self.scheduler.add_job(
                func=self._execute_reminder,
                trigger=trigger,
                args=[reminder_id],
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"Reminder {reminder_id} scheduled for {reminder_time}")
            
            return {
                'success': True,
                'reminder_id': reminder_id,
                'scheduled_time': reminder_time.isoformat(),
                'message': f'Reminder "{title}" scheduled successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_repeat_trigger(self, repeat_pattern: str, start_time: datetime):
        """Create appropriate trigger for repeat pattern."""
        try:
            pattern_lower = repeat_pattern.lower()
            
            if pattern_lower == 'daily':
                return CronTrigger(
                    hour=start_time.hour,
                    minute=start_time.minute,
                    start_date=start_time
                )
            elif pattern_lower == 'weekly':
                return CronTrigger(
                    day_of_week=start_time.weekday(),
                    hour=start_time.hour,
                    minute=start_time.minute,
                    start_date=start_time
                )
            elif pattern_lower == 'monthly':
                return CronTrigger(
                    day=start_time.day,
                    hour=start_time.hour,
                    minute=start_time.minute,
                    start_date=start_time
                )
            elif pattern_lower.startswith('every'):
                # Parse patterns like "every 2 hours", "every 30 minutes"
                parts = pattern_lower.split()
                if len(parts) >= 3:
                    interval = int(parts[1])
                    unit = parts[2].rstrip('s')  # Remove plural 's'
                    
                    if unit == 'minute':
                        return IntervalTrigger(minutes=interval, start_date=start_time)
                    elif unit == 'hour':
                        return IntervalTrigger(hours=interval, start_date=start_time)
                    elif unit == 'day':
                        return IntervalTrigger(days=interval, start_date=start_time)
            
            # Default to one-time trigger
            return DateTrigger(run_date=start_time)
            
        except Exception as e:
            logger.error(f"Error creating repeat trigger: {e}")
            return DateTrigger(run_date=start_time)
    
    def _execute_reminder(self, reminder_id: int):
        """Execute a reminder when it's time."""
        try:
            # Get reminder details from database
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT r.*, u.platform_id, u.platform 
                    FROM reminders r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.id = ? AND r.is_active = 1
                ''', (reminder_id,))
                
                reminder = cursor.fetchone()
                
                if not reminder:
                    logger.warning(f"Reminder {reminder_id} not found or inactive")
                    return
                
                reminder = dict(reminder)
            
            # Send reminder notification
            self._send_reminder_notification(reminder)
            
            # Mark as completed if not repeating
            if not reminder.get('repeat_pattern'):
                self.db.complete_reminder(reminder_id)
                # Remove the job
                try:
                    self.scheduler.remove_job(f"reminder_{reminder_id}")
                except:
                    pass
            
            logger.info(f"Reminder {reminder_id} executed successfully")
            
        except Exception as e:
            logger.error(f"Error executing reminder {reminder_id}: {e}")
    
    def _send_reminder_notification(self, reminder: Dict):
        """Send reminder notification to user."""
        try:
            platform = reminder['platform']
            platform_id = reminder['platform_id']
            title = reminder['title']
            description = reminder['description']
            
            message = f"🔔 **Reminder: {title}**\n\n"
            if description:
                message += f"{description}\n\n"
            message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Send via appropriate platform
            if platform == 'telegram':
                self._send_telegram_reminder(platform_id, message)
            elif platform == 'whatsapp':
                self._send_whatsapp_reminder(platform_id, message)
            
        except Exception as e:
            logger.error(f"Error sending reminder notification: {e}")
    
    def _send_telegram_reminder(self, chat_id: str, message: str):
        """Send reminder via Telegram."""
        try:
            import requests
            import os
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not bot_token:
                logger.warning("TELEGRAM_BOT_TOKEN not set; cannot send Telegram reminder.")
                return
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            resp = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=15)
            if resp.status_code != 200:
                logger.error(f"Telegram reminder send failed: {resp.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram reminder: {e}")
    
    def _send_whatsapp_reminder(self, phone_number: str, message: str):
        """Send reminder via WhatsApp."""
        try:
            import requests
            import os
            access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
            phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
            if not access_token or not phone_number_id:
                logger.warning("WhatsApp credentials missing; cannot send WhatsApp reminder.")
                return
            base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            resp = requests.post(base_url, headers=headers, json=payload, timeout=15)
            if resp.status_code != 200:
                logger.error(f"WhatsApp reminder send failed: {resp.text}")
        except Exception as e:
            logger.error(f"Error sending WhatsApp reminder: {e}")
    
    def get_user_reminders(self, user_id: int) -> List[Dict]:
        """Get all reminders for a user."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM reminders 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY reminder_time ASC
                ''', (user_id,))
                
                reminders = [dict(row) for row in cursor.fetchall()]
                
                # Add job status
                for reminder in reminders:
                    job_id = f"reminder_{reminder['id']}"
                    try:
                        job = self.scheduler.get_job(job_id)
                        reminder['job_status'] = 'scheduled' if job else 'not_scheduled'
                        if job:
                            reminder['next_run_time'] = job.next_run_time.isoformat() if job.next_run_time else None
                    except:
                        reminder['job_status'] = 'unknown'
                
                return reminders
                
        except Exception as e:
            logger.error(f"Error getting user reminders: {e}")
            return []
    
    def cancel_reminder(self, reminder_id: int) -> Dict:
        """Cancel a reminder."""
        try:
            # Deactivate in database
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE reminders 
                    SET is_active = 0 
                    WHERE id = ?
                ''', (reminder_id,))
                conn.commit()
            
            # Remove scheduled job
            job_id = f"reminder_{reminder_id}"
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass  # Job might not exist
            
            return {'success': True, 'message': 'Reminder cancelled successfully'}
            
        except Exception as e:
            logger.error(f"Error cancelling reminder: {e}")
            return {'success': False, 'error': str(e)}
    
    def _cleanup_completed_reminders(self):
        """Clean up old completed reminders."""
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM reminders 
                    WHERE is_completed = 1 AND created_at < ?
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old reminders")
            
        except Exception as e:
            logger.error(f"Error cleaning up reminders: {e}")
    
    def get_active_reminder_count(self) -> int:
        """Get count of active reminders."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM reminders 
                    WHERE is_active = 1 AND is_completed = 0
                ''')
                return cursor.fetchone()['count']
        except Exception as e:
            logger.error(f"Error getting reminder count: {e}")
            return 0
    
    def get_uptime(self) -> str:
        """Get scheduler uptime."""
        try:
            uptime = datetime.now() - self.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            return f"{days}d {hours}h {minutes}m"
        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            return "Unknown"
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.scheduler.running if self.scheduler else False
    
    def get_job_stats(self) -> Dict:
        """Get scheduler job statistics."""
        try:
            jobs = self.scheduler.get_jobs()
            return {
                'total_jobs': len(jobs),
                'running': self.is_running(),
                'uptime': self.get_uptime()
            }
        except Exception as e:
            logger.error(f"Error getting job stats: {e}")
            return {'total_jobs': 0, 'running': False, 'uptime': 'Unknown'}

    def setup_daily_reminders(self, user_id: int):
        sleep_times = [
            (22, 0),  # 10pm
            (23, 0),  # 11pm
            (0, 0),   # 12am
            (1, 0)    # 1am
        ]
        wake_times = [
            (5, 0),   # 5am
            (6, 0),   # 6am
            (7, 0),   # 7am
            (8, 0)    # 8am
        ]
        now = datetime.now()
        for hour, minute in sleep_times:
            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reminder_time < now:
                reminder_time += timedelta(days=1)
            self.create_reminder({
                'user_id': user_id,
                'title': 'Sleep Reminder',
                'description': 'You should sleep early!',
                'reminder_time': reminder_time.isoformat(),
                'repeat_pattern': 'daily'
            })
        for hour, minute in wake_times:
            reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reminder_time < now:
                reminder_time += timedelta(days=1)
            self.create_reminder({
                'user_id': user_id,
                'title': 'Wake Up Reminder',
                'description': 'Have you woken up? Time to start the day!',
                'reminder_time': reminder_time.isoformat(),
                'repeat_pattern': 'daily'
            })
