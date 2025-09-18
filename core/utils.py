import PyPDF2
import os
import tempfile
from typing import Optional

# Text-to-speech disabled for memory optimization

class PDFReader:
    """
    Utility class for reading and extracting text from PDF documents.
    """
    
    def __init__(self):
        pass
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return ""
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get metadata information about a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            dict: PDF metadata
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                info = {
                    'num_pages': len(pdf_reader.pages),
                    'title': pdf_reader.metadata.get('/Title', 'Unknown') if pdf_reader.metadata else 'Unknown',
                    'author': pdf_reader.metadata.get('/Author', 'Unknown') if pdf_reader.metadata else 'Unknown',
                    'subject': pdf_reader.metadata.get('/Subject', 'Unknown') if pdf_reader.metadata else 'Unknown'
                }
                
                return info
                
        except Exception as e:
            print(f"Error getting PDF info for {pdf_path}: {e}")
            return {}


class TextToSpeech:
    """Text-to-speech disabled for memory optimization."""
    
    def __init__(self):
        pass
    
    def text_to_speech(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """Text-to-speech disabled for memory optimization."""
        return None
    
    def speak_text(self, text: str):
        """Text-to-speech disabled for memory optimization."""
        pass
    
    def set_voice_properties(self, rate: int = 180, volume: float = 0.9, voice_id: Optional[str] = None):
        """Text-to-speech disabled for memory optimization."""
        pass
    
    def get_available_voices(self) -> list:
        """Text-to-speech disabled for memory optimization."""
        return []


class AudioProcessor:
    """
    Utility class for audio file processing and conversion.
    """
    
    @staticmethod
    def convert_audio_format(input_path: str, output_path: str, output_format: str = "wav") -> bool:
        """
        Convert audio file to different format.
        
        Args:
            input_path (str): Path to input audio file
            output_path (str): Path for output audio file
            output_format (str): Target format (wav, mp3, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(input_path)
            audio.export(output_path, format=output_format)
            return True
            
        except Exception as e:
            print(f"Error converting audio format: {e}")
            return False
    
    @staticmethod
    def get_audio_duration(file_path: str) -> Optional[float]:
        """
        Get duration of audio file in seconds.
        
        Args:
            file_path (str): Path to audio file
            
        Returns:
            float: Duration in seconds, or None if failed
        """
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0  # Convert milliseconds to seconds
            
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return None


class FileManager:
    """
    Utility class for file management operations.
    """
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> bool:
        """
        Ensure a directory exists, create if it doesn't.
        
        Args:
            directory_path (str): Path to directory
            
        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {directory_path}: {e}")
            return False
    
    @staticmethod
    def clean_temp_files(temp_dir: str, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.
        
        Args:
            temp_dir (str): Directory containing temporary files
            max_age_hours (int): Maximum age in hours before deletion
            
        Returns:
            int: Number of files deleted
        """
        try:
            import time
            
            if not os.path.exists(temp_dir):
                return 0
            
            deleted_count = 0
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning temp files: {e}")
            return 0
