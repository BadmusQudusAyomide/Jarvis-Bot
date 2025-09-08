import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import json
import os
from PIL import Image
import requests
from io import BytesIO

class CalculatorTools:
    """
    Advanced calculator and mathematical operations.
    """
    
    @staticmethod
    def evaluate_expression(expression: str) -> Dict:
        """
        Safely evaluate mathematical expressions.
        
        Args:
            expression (str): Mathematical expression
            
        Returns:
            Dict: Result and status
        """
        try:
            # Remove spaces and validate expression
            expression = expression.replace(' ', '')
            
            # Allow only safe characters
            allowed_chars = set('0123456789+-*/().^%sincotan√πe')
            if not all(c.lower() in allowed_chars for c in expression):
                return {'error': 'Invalid characters in expression', 'status': 'error'}
            
            # Replace common mathematical symbols
            expression = expression.replace('^', '**')
            expression = expression.replace('π', str(math.pi))
            expression = expression.replace('e', str(math.e))
            expression = expression.replace('√', 'math.sqrt')
            
            # Handle trigonometric functions
            expression = re.sub(r'sin\(([^)]+)\)', r'math.sin(\1)', expression)
            expression = re.sub(r'cos\(([^)]+)\)', r'math.cos(\1)', expression)
            expression = re.sub(r'tan\(([^)]+)\)', r'math.tan(\1)', expression)
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}, "math": math})
            
            return {
                'expression': expression,
                'result': result,
                'formatted_result': f"{result:,.6f}".rstrip('0').rstrip('.'),
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'Calculation error: {str(e)}', 'status': 'error'}
    
    @staticmethod
    def convert_units(value: float, from_unit: str, to_unit: str) -> Dict:
        """
        Convert between different units.
        
        Args:
            value (float): Value to convert
            from_unit (str): Source unit
            to_unit (str): Target unit
            
        Returns:
            Dict: Conversion result
        """
        # Unit conversion factors to base units
        conversions = {
            # Length (to meters)
            'mm': 0.001, 'cm': 0.01, 'm': 1, 'km': 1000,
            'in': 0.0254, 'ft': 0.3048, 'yd': 0.9144, 'mi': 1609.34,
            
            # Weight (to grams)
            'mg': 0.001, 'g': 1, 'kg': 1000, 't': 1000000,
            'oz': 28.3495, 'lb': 453.592,
            
            # Temperature (special handling)
            'c': 'celsius', 'f': 'fahrenheit', 'k': 'kelvin',
            
            # Volume (to liters)
            'ml': 0.001, 'l': 1, 'gal': 3.78541, 'qt': 0.946353,
            'cup': 0.236588, 'tbsp': 0.0147868, 'tsp': 0.00492892
        }
        
        try:
            from_unit = from_unit.lower()
            to_unit = to_unit.lower()
            
            # Handle temperature conversions separately
            if from_unit in ['c', 'f', 'k'] or to_unit in ['c', 'f', 'k']:
                return CalculatorTools._convert_temperature(value, from_unit, to_unit)
            
            # Check if units exist
            if from_unit not in conversions or to_unit not in conversions:
                return {'error': 'Unknown unit', 'status': 'error'}
            
            # Convert to base unit, then to target unit
            base_value = value * conversions[from_unit]
            result = base_value / conversions[to_unit]
            
            return {
                'original_value': value,
                'original_unit': from_unit,
                'converted_value': result,
                'converted_unit': to_unit,
                'formatted_result': f"{result:,.6f}".rstrip('0').rstrip('.'),
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'Conversion error: {str(e)}', 'status': 'error'}
    
    @staticmethod
    def _convert_temperature(value: float, from_unit: str, to_unit: str) -> Dict:
        """Convert temperature between Celsius, Fahrenheit, and Kelvin."""
        try:
            # Convert to Celsius first
            if from_unit == 'f':
                celsius = (value - 32) * 5/9
            elif from_unit == 'k':
                celsius = value - 273.15
            else:  # from_unit == 'c'
                celsius = value
            
            # Convert from Celsius to target
            if to_unit == 'f':
                result = celsius * 9/5 + 32
            elif to_unit == 'k':
                result = celsius + 273.15
            else:  # to_unit == 'c'
                result = celsius
            
            return {
                'original_value': value,
                'original_unit': from_unit.upper(),
                'converted_value': result,
                'converted_unit': to_unit.upper(),
                'formatted_result': f"{result:.2f}",
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'Temperature conversion error: {str(e)}', 'status': 'error'}


class TaskScheduler:
    """
    Task scheduling and reminder system.
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.tasks_file = os.path.join(data_dir, 'scheduled_tasks.json')
        self.tasks = self._load_tasks()
    
    def _load_tasks(self) -> List[Dict]:
        """Load tasks from file."""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception:
            return []
    
    def _save_tasks(self):
        """Save tasks to file."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.tasks_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")
    
    def add_task(self, title: str, description: str, due_date: str, priority: str = 'medium') -> Dict:
        """
        Add a new task.
        
        Args:
            title (str): Task title
            description (str): Task description
            due_date (str): Due date in format 'YYYY-MM-DD HH:MM'
            priority (str): Priority level (low, medium, high)
            
        Returns:
            Dict: Result status
        """
        try:
            # Parse due date
            due_datetime = datetime.strptime(due_date, '%Y-%m-%d %H:%M')
            
            task = {
                'id': len(self.tasks) + 1,
                'title': title,
                'description': description,
                'due_date': due_date,
                'due_timestamp': due_datetime.timestamp(),
                'priority': priority,
                'completed': False,
                'created_at': datetime.now().isoformat()
            }
            
            self.tasks.append(task)
            self._save_tasks()
            
            return {
                'message': f'Task "{title}" scheduled for {due_date}',
                'task_id': task['id'],
                'status': 'success'
            }
            
        except ValueError:
            return {'error': 'Invalid date format. Use YYYY-MM-DD HH:MM', 'status': 'error'}
        except Exception as e:
            return {'error': f'Error adding task: {str(e)}', 'status': 'error'}
    
    def get_upcoming_tasks(self, days_ahead: int = 7) -> List[Dict]:
        """Get tasks due within specified days."""
        try:
            now = datetime.now().timestamp()
            future = (datetime.now() + timedelta(days=days_ahead)).timestamp()
            
            upcoming = []
            for task in self.tasks:
                if not task['completed'] and now <= task['due_timestamp'] <= future:
                    upcoming.append(task)
            
            # Sort by due date
            upcoming.sort(key=lambda x: x['due_timestamp'])
            return upcoming
            
        except Exception as e:
            print(f"Error getting upcoming tasks: {e}")
            return []
    
    def complete_task(self, task_id: int) -> Dict:
        """Mark a task as completed."""
        try:
            for task in self.tasks:
                if task['id'] == task_id:
                    task['completed'] = True
                    task['completed_at'] = datetime.now().isoformat()
                    self._save_tasks()
                    return {'message': f'Task "{task["title"]}" marked as completed', 'status': 'success'}
            
            return {'error': 'Task not found', 'status': 'error'}
            
        except Exception as e:
            return {'error': f'Error completing task: {str(e)}', 'status': 'error'}


class ImageAnalyzer:
    """
    Image analysis and processing tools.
    """
    
    @staticmethod
    def analyze_image(image_path: str) -> Dict:
        """
        Analyze an image and extract information.
        
        Args:
            image_path (str): Path to image file
            
        Returns:
            Dict: Image analysis results
        """
        try:
            with Image.open(image_path) as img:
                # Basic image information
                info = {
                    'filename': os.path.basename(image_path),
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'aspect_ratio': round(img.width / img.height, 2),
                    'file_size': os.path.getsize(image_path),
                    'status': 'success'
                }
                
                # Color analysis
                if img.mode == 'RGB':
                    colors = img.getcolors(maxcolors=256*256*256)
                    if colors:
                        # Get dominant color
                        dominant_color = max(colors, key=lambda x: x[0])[1]
                        info['dominant_color'] = {
                            'rgb': dominant_color,
                            'hex': '#{:02x}{:02x}{:02x}'.format(*dominant_color)
                        }
                
                # Image quality assessment
                if img.width * img.height > 1000000:  # > 1MP
                    info['quality'] = 'High resolution'
                elif img.width * img.height > 300000:  # > 0.3MP
                    info['quality'] = 'Medium resolution'
                else:
                    info['quality'] = 'Low resolution'
                
                return info
                
        except Exception as e:
            return {'error': f'Image analysis error: {str(e)}', 'status': 'error'}
    
    @staticmethod
    def resize_image(image_path: str, output_path: str, max_width: int = 800, max_height: int = 600) -> Dict:
        """
        Resize an image while maintaining aspect ratio.
        
        Args:
            image_path (str): Input image path
            output_path (str): Output image path
            max_width (int): Maximum width
            max_height (int): Maximum height
            
        Returns:
            Dict: Resize operation result
        """
        try:
            with Image.open(image_path) as img:
                # Calculate new size maintaining aspect ratio
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                img.save(output_path, optimize=True, quality=85)
                
                return {
                    'original_size': Image.open(image_path).size,
                    'new_size': img.size,
                    'output_path': output_path,
                    'compression_ratio': round(os.path.getsize(output_path) / os.path.getsize(image_path), 2),
                    'status': 'success'
                }
                
        except Exception as e:
            return {'error': f'Image resize error: {str(e)}', 'status': 'error'}


class TextAnalyzer:
    """
    Advanced text analysis tools.
    """
    
    @staticmethod
    def analyze_text(text: str) -> Dict:
        """
        Analyze text for various metrics.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            Dict: Text analysis results
        """
        try:
            # Basic metrics
            words = text.split()
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Character analysis
            char_count = len(text)
            char_count_no_spaces = len(text.replace(' ', ''))
            word_count = len(words)
            sentence_count = len(sentences)
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
            
            # Reading metrics
            avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
            avg_chars_per_word = char_count_no_spaces / word_count if word_count > 0 else 0
            
            # Estimated reading time (average 200 words per minute)
            reading_time_minutes = word_count / 200
            
            # Most common words (excluding common stop words)
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
            
            word_freq = {}
            for word in words:
                clean_word = re.sub(r'[^\w]', '', word.lower())
                if clean_word and clean_word not in stop_words and len(clean_word) > 2:
                    word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
            
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'character_count': char_count,
                'character_count_no_spaces': char_count_no_spaces,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count,
                'average_words_per_sentence': round(avg_words_per_sentence, 2),
                'average_characters_per_word': round(avg_chars_per_word, 2),
                'estimated_reading_time_minutes': round(reading_time_minutes, 1),
                'top_words': top_words,
                'status': 'success'
            }
            
        except Exception as e:
            return {'error': f'Text analysis error: {str(e)}', 'status': 'error'}
    
    @staticmethod
    def extract_entities(text: str) -> Dict:
        """
        Extract entities like emails, URLs, phone numbers from text.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            Dict: Extracted entities
        """
        try:
            # Regular expressions for common entities
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
            
            entities = {
                'emails': re.findall(email_pattern, text),
                'urls': re.findall(url_pattern, text),
                'phone_numbers': re.findall(phone_pattern, text),
                'dates': re.findall(date_pattern, text),
                'status': 'success'
            }
            
            return entities
            
        except Exception as e:
            return {'error': f'Entity extraction error: {str(e)}', 'status': 'error'}
