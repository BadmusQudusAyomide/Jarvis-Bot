import os
import yt_dlp
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    """Handles YouTube video/audio downloads"""
    
    def __init__(self, download_dir: str = None):
        """
        Args:
            download_dir: Directory to save downloaded files (default: data/downloads)
        """
        self.download_dir = download_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'downloads'
        )
        os.makedirs(self.download_dir, exist_ok=True)
    
    def get_video_info(self, url: str) -> Optional[Dict]:
        """Get video information without downloading"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Untitled'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'formats': info.get('formats', []),
                    'best_quality': self._get_best_quality(info.get('formats', []))
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def _get_best_quality(self, formats: list) -> Dict:
        """Find the best quality format"""
        best = {'height': 0, 'url': None}
        for f in formats:
            if f.get('height') and f.get('height') > best['height'] and f.get('url'):
                best = {
                    'height': f['height'],
                    'url': f['url'],
                    'ext': f.get('ext', 'mp4')
                }
        return best
    
    def _normalize_quality(self, quality: str) -> Optional[int]:
        """Normalize quality string like '240p'/'360p' to integer height.
        Returns None for 'best'."""
        try:
            if not quality or quality == 'best':
                return None
            q = quality.strip().lower().replace('p', '')
            if q.isdigit():
                return int(q)
            return None
        except Exception:
            return None

    def download_video(self, url: str, quality: str = 'best') -> Tuple[Optional[str], Optional[str]]:
        """
        Download YouTube video
        
        Args:
            url: YouTube URL
            quality: 'best', '720p', '480p', '360p', etc.
            
        Returns:
            Tuple of (file_path, error_message)
        """
        try:
            height = self._normalize_quality(quality)
            # Domain-specific handling
            domain = ''
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
            except Exception:
                pass

            # Default format selector (YouTube etc.)
            format_selector = 'best'
            if height:
                format_selector = f'bv*[height<={height}]+ba/b[height<={height}]'

            # Instagram, TikTok, and Facebook often don't expose clean height-filtered formats; use more permissive selector\n            if 'instagram.com' in domain or 'instagr.am' in domain or 'tiktok.com' in domain or 'vm.tiktok.com' in domain or 'facebook.com' in domain or 'fb.watch' in domain or 'm.facebook.com' in domain:\n                format_selector = 'b[ext=mp4]/b/best'\n\n            ydl_opts = {\n                'format': format_selector,\n                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),\n                'merge_output_format': 'mp4',\n                'postprocessors': [{\n                    'key': 'FFmpegVideoConvertor',\n                    'preferedformat': 'mp4',\n                }],\n                'noplaylist': True,\n                'quiet': False,\n                'no_warnings': False,\n            }\n\n            # Set headers to improve extraction reliability\n            ydl_opts['http_headers'] = {\n                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36',\n                'Referer': url\n            }\n\n            # Optional cookies support\n            import os as _os\n            ig_cookie_path = _os.getenv('INSTAGRAM_COOKIES')\n            ig_sessionid = _os.getenv('INSTAGRAM_SESSIONID')\n            fb_cookie_path = _os.getenv('FACEBOOK_COOKIES')\n            fb_sessionid = _os.getenv('FACEBOOK_SESSIONID')\n\n            if 'instagram.com' in domain or 'instagr.am' in domain:\n                if ig_cookie_path and _os.path.exists(ig_cookie_path):\n                    ydl_opts['cookiefile'] = ig_cookie_path\n                elif ig_sessionid:\n                    # Minimal cookie jar using sessionid; works for some endpoints\n                    ydl_opts.setdefault('cookiesfrombrowser', []).append(('instagram', None, None, None))\n                    # Alternatively, manual cookie\n                    ydl_opts.setdefault('cookies', []).append({'domain': '.instagram.com', 'name': 'sessionid', 'value': ig_sessionid})\n\n            if 'facebook.com' in domain or 'fb.watch' in domain or 'm.facebook.com' in domain:\n                if fb_cookie_path and _os.path.exists(fb_cookie_path):\n                    ydl_opts['cookiefile'] = fb_cookie_path\n                elif fb_sessionid:\n                    ydl_opts.setdefault('cookies', []).append({'domain': '.facebook.com', 'name': 'c_user', 'value': fb_sessionid})  # Note: Facebook uses multiple cookies; this is basic\n\n            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Ensure the file has .mp4 extension
                base, ext = os.path.splitext(filename)
                if ext.lower() not in ['.mp4', '.mkv', '.webm']:
                    new_filename = f"{base}.mp4"
                    os.rename(filename, new_filename)
                    filename = new_filename
                
                return filename, None
                
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None, str(e)
    
    def download_audio(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download YouTube audio as MP3
        
        Returns:
            Tuple of (file_path, error_message)
        """
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': False,
                'no_warnings': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base = os.path.splitext(ydl.prepare_filename(info))[0]
                return f"{base}.mp3", None
                
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None, str(e)
