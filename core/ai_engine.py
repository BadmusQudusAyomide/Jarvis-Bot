import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None
    np = None

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    whisper = None

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False
    yt_dlp = None

import requests
import tempfile
import google.generativeai as genai
import openai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIEngine:
    """
    Comprehensive AI engine with multiple capabilities:
    - Text generation (Gemini/OpenAI)
    - Embeddings and semantic search
    - Speech-to-text (Whisper)
    - Image generation (DALL-E)
    - Media processing
    """
    
    def __init__(self):
        # Initialize LLM
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        gemini_keys_env = os.getenv('GEMINI_API_KEYS', '')
        self.gemini_keys = [k.strip() for k in gemini_keys_env.split(',') if k.strip()]
        if self.gemini_api_key and self.gemini_api_key not in self.gemini_keys:
            self.gemini_keys.insert(0, self.gemini_api_key)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if self.gemini_keys:
            # Configure with first key; per-call we may rotate
            genai.configure(api_key=self.gemini_keys[0])
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            self.llm_provider = 'gemini'
        elif self.openai_api_key:
            openai.api_key = self.openai_api_key
            self.llm_provider = 'openai'
        else:
            raise ValueError("No LLM API key found. Set GEMINI_API_KEY/GEMINI_API_KEYS or OPENAI_API_KEY")
        
        # Initialize embeddings model
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}")
                self.embedding_model = None
        else:
            logger.warning("Sentence transformers not available. Semantic search disabled.")
            self.embedding_model = None
        
        # Initialize Whisper for speech-to-text
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.whisper_model = None
        
        # Document storage
        self.documents_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'documents')
        os.makedirs(self.documents_path, exist_ok=True)
        
        logger.info(f"AI Engine initialized with {self.llm_provider}")
    
    def generate_response(self, prompt: str, context: Dict = None, max_tokens: int = 1000) -> str:\n    """\n    Generate AI response using configured LLM.\n    \n    Args:\n        prompt (str): User prompt\n        context (Dict): Additional context\n        max_tokens (int): Maximum response tokens\n        \n    Returns:\n        str: Generated response\n    """\n    try:\n        # Build full prompt with context\n        full_prompt = self._build_prompt_with_context(prompt, context)\n        \n        if self.llm_provider == 'gemini':\n            # Try each Gemini key until success\n            last_err = None\n            for key in self.gemini_keys:\n                try:\n                    genai.configure(api_key=key)\n                    model = genai.GenerativeModel('gemini-1.5-flash')\n                    response = model.generate_content(full_prompt)\n                    return response.text.strip()\n                except Exception as e:\n                    last_err = e\n                    continue\n            # Fallback to OpenAI if available\n            if self.openai_api_key:\n                response = openai.ChatCompletion.create(\n                    model="gpt-3.5-turbo",\n                    messages=[\n                        {"role": "system", "content": "You are Jarvis, an intelligent AI assistant."},\n                        {"role": "user", "content": full_prompt}\n                    ],\n                    max_tokens=max_tokens,\n                    temperature=0.7\n                )\n                return response.choices[0].message.content.strip()\n            raise last_err or RuntimeError("Gemini request failed")\n        \n        elif self.llm_provider == 'openai':\n            response = openai.ChatCompletion.create(\n                model="gpt-3.5-turbo",\n                messages=[\n                    {"role": "system", "content": "You are Jarvis, an intelligent AI assistant."},\n                    {"role": "user", "content": full_prompt}\n                ],\n                max_tokens=max_tokens,\n                temperature=0.7\n            )\n            return response.choices[0].message.content.strip()\n        \n    except Exception as e:\n        logger.error(f"Error generating response: {e}")\n        return "I apologize, but I'm having trouble processing your request right now. Please try again."
    
    def _build_prompt_with_context(self, prompt: str, context: Dict = None) -> str:
        """Build prompt with relevant context."""
        base_prompt = """You are Jarvis, an advanced AI assistant with the following capabilities:

🧠 Core Functions:
- Answer questions and provide information
- Analyze documents and images
- Generate creative content
- Perform calculations and conversions
- Search the web for real-time information
- Manage tasks and reminders
- Process voice messages

🌐 Real-time Capabilities:
- Weather information
- Latest news
- Cryptocurrency prices
- Web search
- Translation services

🔧 Tools Available:
- Calculator and unit converter
- Task scheduler
- Document analysis
- Image processing
- Media downloading

Be helpful, accurate, and engaging. If you don't know something, be honest about it."""
        
        if context:
            if context.get('user_documents'):
                base_prompt += f"\n\nRelevant documents: {context['user_documents']}"
            if context.get('conversation_history'):
                base_prompt += f"\n\nRecent conversation: {context['conversation_history']}"
            if context.get('user_preferences'):
                base_prompt += f"\n\nUser preferences: {context['user_preferences']}"
        
        return f"{base_prompt}\n\nUser: {prompt}\n\nJarvis:"
    
    def generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generate embeddings for text."""
        if not text or not self.embedding_model:
            return None
        
        try:
            embedding = self.embedding_model.encode([text])
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def semantic_search(self, query: str, documents: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Perform semantic search on documents.
        
        Args:
            query (str): Search query
            documents (List[Dict]): Documents with embeddings
            top_k (int): Number of results to return
            
        Returns:
            List[Dict]: Ranked documents
        """
        if not self.embedding_model:
            return documents[:top_k]
        
        try:
            query_embedding = self.generate_embeddings(query)
            if not query_embedding:
                return documents[:top_k]
            
            scored_docs = []
            for doc in documents:
                if doc.get('embeddings'):
                    doc_embedding = json.loads(doc['embeddings'])
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    scored_docs.append({**doc, 'similarity': similarity})
            
            # Sort by similarity and return top_k
            scored_docs.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return documents[:top_k]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        except:
            return 0.0
    
    def transcribe_audio(self, audio_path: str) -> Tuple[str, bool]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_path (str): Path to audio file
            
        Returns:
            Tuple[str, bool]: (transcribed_text, success)
        """
        if not self.whisper_model:
            return "Speech recognition not available", False
        
        if not HAS_WHISPER:
            logger.warning("Whisper not available for speech-to-text")
            return None
            
        try:
            # Load Whisper model
            model = whisper.load_model("base")
            
            # Transcribe audio
            result = model.transcribe(audio_path)
            return result["text"]
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """
        Generate an image using the configured provider.
        - If provider is Gemini, use the specified image-capable model (default: gemini-2.5-flash-image-preview)
        - If provider is OpenAI, fallback to DALL·E via Images API and return URL
        Returns a local file path (Gemini) or URL (OpenAI) on success.
        """
        try:
            # Gemini image generation path
            if self.llm_provider == 'gemini' and self.gemini_keys:
                model_id = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image-preview')
                last_err = None
                for key in self.gemini_keys:
                    try:
                        genai.configure(api_key=key)
                        model = genai.GenerativeModel(model_id)
                        # Request binary image if supported
                        try:
                            response = model.generate_content(
                                prompt,
                                generation_config={"response_mime_type": "image/png"}
                            )
                        except Exception:
                            response = model.generate_content(prompt)
                        
                        # Extract inline image bytes from candidates parts
                        image_bytes = None
                        try:
                            candidates = getattr(response, 'candidates', []) or []
                            for cand in candidates:
                                content = getattr(cand, 'content', None)
                                parts = getattr(content, 'parts', []) if content else []
                                for part in parts:
                                    inline = getattr(part, 'inline_data', None)
                                    if inline is None and isinstance(part, dict):
                                        inline = part.get('inline_data')
                                    if not inline:
                                        continue
                                    data = getattr(inline, 'data', None)
                                    if data is None and isinstance(inline, dict):
                                        data = inline.get('data')
                                    if not data:
                                        continue
                                    if isinstance(data, (bytes, bytearray)):
                                        image_bytes = bytes(data)
                                        break
                                    else:
                                        import base64
                                        try:
                                            image_bytes = base64.b64decode(data)
                                            break
                                        except Exception:
                                            continue
                                if image_bytes:
                                    break
                        except Exception:
                            image_bytes = None
                        
                        if image_bytes:
                            out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'documents', 'generated')
                            os.makedirs(out_dir, exist_ok=True)
                            filename = f"gemini_img_{int(datetime.now().timestamp())}.png"
                            out_path = os.path.join(out_dir, filename)
                            with open(out_path, 'wb') as f:
                                f.write(image_bytes)
                            return out_path
                        # No inline image: return text URL if provided
                        try:
                            text = (getattr(response, 'text', None) or '').strip()
                            if text and text.startswith('http'):
                                return text
                        except Exception:
                            pass
                        # If we reached here, this key produced no usable output; try next
                        last_err = RuntimeError("No image bytes or URL in response")
                        continue
                    except Exception as e:
                        last_err = e
                        continue
                # All keys failed
                logger.error(f"Gemini image generation failed across keys: {last_err}")
                return None

            # OpenAI fallback
            if self.llm_provider == 'openai' and self.openai_api_key:
                response = openai.Image.create(
                    prompt=prompt,
                    n=1,
                    size=size
                )
                return response['data'][0]['url']
            
            return None
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None
    
    def download_media(self, url: str, media_type: str = 'video') -> Optional[str]:
        """
        Download media from URL using yt-dlp.
        
        Args:
            url (str): Media URL
            media_type (str): 'video' or 'audio'
            
        Returns:
            Optional[str]: Path to downloaded file
        """
        if not HAS_YT_DLP:
            logger.warning("yt-dlp not available for media download")
            return None
            
        try:
            import os
            
            # Configure yt-dlp options
            if media_type == "audio":
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(self.documents_path, '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
            else:
                ydl_opts = {
                    'format': 'best[height<=720]',
                    'outtmpl': os.path.join(self.documents_path, '%(title)s.%(ext)s'),
                }
            
            # Download with yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # For audio, the filename might change after post-processing
                if media_type == "audio":
                    base_filename = os.path.splitext(filename)[0]
                    audio_filename = base_filename + '.mp3'
                    if os.path.exists(audio_filename):
                        return audio_filename
                
                return filename if os.path.exists(filename) else None
                    
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None
    
    def analyze_image(self, image_path: str) -> Dict:
        """
        Analyze image and extract information.
        
        Args:
            image_path (str): Path to image
            
        Returns:
            Dict: Analysis results
        """
        if not HAS_PIL:
            logger.warning("PIL not available for image processing")
            return None
            
        try:
            # Open and analyze image
            with Image.open(image_path) as img:
                # Get basic info
                info = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height
                }
                
                return info
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {'error': str(e)}
    
    def add_document(self, file, user_id: str) -> Dict:
        """
        Process and add document to knowledge base.
        
        Args:
            file: Uploaded file object
            user_id (str): User identifier
            
        Returns:
            Dict: Processing result
        """
        try:
            # Save file
            filename = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            file_path = os.path.join(self.documents_path, filename)
            file.save(file_path)
            
            # Extract text content
            content = self._extract_text_from_file(file_path)
            
            # Generate embeddings
            embeddings = None
            if content and self.embedding_model:
                embeddings = self.generate_embeddings(content[:1000])  # First 1000 chars
            
            # Generate summary
            summary = self._generate_summary(content) if content else "No content extracted"
            
            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'content_length': len(content) if content else 0,
                'summary': summary,
                'embeddings': json.dumps(embeddings) if embeddings else None
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_text_from_file(self, file_path: str) -> Optional[str]:
        """Extract text from various file formats."""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                import PyPDF2
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                    return text
            
            elif file_ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            elif file_ext in ['.docx']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                except ImportError:
                    logger.warning("python-docx not installed, cannot process .docx files")
                    return None
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return None
    
    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate summary of content."""
        if not content:
            return "No content to summarize"
        
        # Simple extractive summary - take first few sentences
        sentences = content.split('. ')
        summary = '. '.join(sentences[:3])
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    def health_check(self) -> bool:
        """Check AI engine health."""
        try:
            # Test LLM
            test_response = self.generate_response("Hello", max_tokens=10)
            return bool(test_response)
        except Exception as e:
            logger.error(f"AI engine health check failed: {e}")
            return False
