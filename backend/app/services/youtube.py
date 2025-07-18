import asyncio
import logging
import os
import tempfile
import uuid
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
import yt_dlp
from app.config import settings

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self):
        self.temp_dir = settings.TEMP_DIR
        self.max_duration = getattr(settings, 'YOUTUBE_MAX_DURATION', 3600)  # 1 hour default
        self.max_file_size = getattr(settings, 'YOUTUBE_MAX_FILE_SIZE', settings.MAX_FILE_SIZE)
        
    async def validate_youtube_url(self, url: str) -> Dict[str, Any]:
        """Validate YouTube URL and extract video information"""
        try:
            # Check if URL is a valid YouTube URL
            if not self._is_valid_youtube_url(url):
                raise ValueError("Invalid YouTube URL format")
            
            # Extract video info without downloading
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self._get_video_info, url)
            
            # Validate video constraints
            duration = info.get('duration', 0)
            if duration > self.max_duration:
                raise ValueError(f"Video duration ({duration}s) exceeds maximum allowed ({self.max_duration}s)")
            
            # Check if video is available
            if info.get('availability') not in [None, 'public', 'unlisted']:
                raise ValueError("Video is not publicly available")
            
            return {
                'valid': True,
                'title': info.get('title', 'Unknown'),
                'duration': duration,
                'uploader': info.get('uploader', 'Unknown'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count'),
                'description': info.get('description', '')[:200] + '...' if info.get('description', '') else '',
                'thumbnail': info.get('thumbnail'),
                'video_id': info.get('id'),
                'formats_available': len(info.get('formats', []))
            }
            
        except Exception as e:
            logger.error(f"YouTube URL validation failed: {str(e)}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _is_valid_youtube_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        try:
            parsed = urlparse(url)
            
            # Check for various YouTube URL formats
            youtube_domains = ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
            
            if parsed.netloc in youtube_domains:
                if parsed.netloc == 'youtu.be':
                    # Short URL format: https://youtu.be/VIDEO_ID
                    return len(parsed.path) > 1
                else:
                    # Long URL format: https://youtube.com/watch?v=VIDEO_ID
                    query_params = parse_qs(parsed.query)
                    return 'v' in query_params and len(query_params['v'][0]) > 0
            
            return False
            
        except Exception:
            return False
    
    def _get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video information using yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    
    async def download_audio(self, url: str, output_format: str = 'mp3') -> Dict[str, Any]:
        """Download audio from YouTube video"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            output_path = os.path.join(self.temp_dir, f"{file_id}.{output_format}")
            
            # Configure yt-dlp options for audio extraction
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path.replace(f'.{output_format}', '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': output_format,
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'extractaudio': True,
                'audioformat': output_format,
                'embed_subs': False,
                'writesubtitles': False,
            }
            
            # Download audio in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._download_with_ydl, url, ydl_opts)
            
            # Find the actual downloaded file
            actual_path = self._find_downloaded_file(output_path, output_format)
            
            if not actual_path or not os.path.exists(actual_path):
                raise Exception("Downloaded file not found")
            
            # Get file information
            file_size = os.path.getsize(actual_path)
            if file_size > self.max_file_size:
                os.remove(actual_path)
                raise ValueError(f"Downloaded file size ({file_size} bytes) exceeds maximum allowed ({self.max_file_size} bytes)")
            
            # Get audio duration using yt-dlp info
            info = result.get('info', {})
            duration = info.get('duration', 0)
            
            return {
                'success': True,
                'file_path': actual_path,
                'file_size': file_size,
                'duration': duration,
                'format': output_format,
                'title': info.get('title', 'Unknown'),
                'video_id': info.get('id'),
                'metadata': {
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'original_url': url
                }
            }
            
        except Exception as e:
            logger.error(f"YouTube audio download failed: {str(e)}")
            # Clean up any partial files
            try:
                if 'actual_path' in locals() and os.path.exists(actual_path):
                    os.remove(actual_path)
            except:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _download_with_ydl(self, url: str, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        """Download using yt-dlp in synchronous context"""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {'info': info}
    
    def _find_downloaded_file(self, base_path: str, expected_format: str) -> Optional[str]:
        """Find the actual downloaded file (yt-dlp may change the extension)"""
        base_name = os.path.splitext(base_path)[0]
        
        # Common audio formats that yt-dlp might use
        possible_extensions = [expected_format, 'mp3', 'webm', 'm4a', 'ogg', 'wav']
        
        for ext in possible_extensions:
            potential_path = f"{base_name}.{ext}"
            if os.path.exists(potential_path):
                return potential_path
        
        # If exact match not found, look for any file with the base name
        import glob
        pattern = f"{base_name}.*"
        matches = glob.glob(pattern)
        
        if matches:
            # Return the first match
            return matches[0]
        
        return None
    
    async def get_video_metadata(self, url: str) -> Dict[str, Any]:
        """Get comprehensive video metadata"""
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self._get_detailed_info, url)
            
            return {
                'success': True,
                'metadata': {
                    'title': info.get('title'),
                    'description': info.get('description'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'comment_count': info.get('comment_count'),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'thumbnail': info.get('thumbnail'),
                    'video_id': info.get('id'),
                    'channel': info.get('channel'),
                    'channel_id': info.get('channel_id'),
                    'language': info.get('language'),
                    'subtitles': list(info.get('subtitles', {}).keys()) if info.get('subtitles') else [],
                    'automatic_captions': list(info.get('automatic_captions', {}).keys()) if info.get('automatic_captions') else []
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get video metadata: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_detailed_info(self, url: str) -> Dict[str, Any]:
        """Get detailed video information"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    
    async def extract_subtitles(self, url: str, language: str = 'en') -> Dict[str, Any]:
        """Extract subtitles from YouTube video if available"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._extract_subtitles_sync, url, language)
            
            return {
                'success': True,
                'subtitles': result.get('subtitles', ''),
                'language': language,
                'source': result.get('source', 'unknown')  # 'manual' or 'automatic'
            }
            
        except Exception as e:
            logger.error(f"Subtitle extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_subtitles_sync(self, url: str, language: str) -> Dict[str, Any]:
        """Extract subtitles synchronously"""
        temp_file = os.path.join(self.temp_dir, f"subs_{uuid.uuid4()}.vtt")
        
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language],
            'skip_download': True,
            'outtmpl': temp_file.replace('.vtt', '.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Look for subtitle files
                subtitle_files = []
                base_name = temp_file.replace('.vtt', '')
                
                import glob
                for pattern in [f"{base_name}.{language}.vtt", f"{base_name}.*.vtt"]:
                    subtitle_files.extend(glob.glob(pattern))
                
                if subtitle_files:
                    # Read the first subtitle file found
                    with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Clean up subtitle files
                    for file in subtitle_files:
                        try:
                            os.remove(file)
                        except:
                            pass
                    
                    # Determine source type
                    source = 'automatic' if 'automatic_captions' in str(subtitle_files[0]) else 'manual'
                    
                    return {
                        'subtitles': content,
                        'source': source
                    }
                else:
                    return {'subtitles': '', 'source': 'none'}
                    
        except Exception as e:
            # Clean up any temp files
            import glob
            for temp_file in glob.glob(f"{temp_file.replace('.vtt', '')}*"):
                try:
                    os.remove(temp_file)
                except:
                    pass
            raise e
    
    async def cleanup_temp_files(self, file_path: str):
        """Clean up temporary downloaded files"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites by yt-dlp"""
        try:
            # Get a sample of supported extractors
            extractors = yt_dlp.extractor.gen_extractor_classes()
            sites = []
            
            for extractor in list(extractors)[:50]:  # Limit to first 50 for performance
                if hasattr(extractor, 'IE_NAME') and extractor.IE_NAME:
                    sites.append(extractor.IE_NAME)
            
            return sorted(sites)
            
        except Exception as e:
            logger.error(f"Failed to get supported sites: {str(e)}")
            return ['youtube', 'youtu.be']  # Fallback to basic YouTube support

# Global YouTube service instance
youtube_service = YouTubeService()