import os
import tempfile
import logging
import filetype
import asyncio
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
from supabase import create_client, Client
from storage3 import create_client as create_storage_client
from app.config import settings
from app.models.schemas import FileMetadata
import uuid

logger = logging.getLogger(__name__)

class FileHandlerService:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.storage_client = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Initialize Supabase client"""
        try:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                self.storage_client = create_storage_client(
                    settings.SUPABASE_URL + "/storage/v1",
                    {"Authorization": f"Bearer {settings.SUPABASE_KEY}"}
                )
                logger.info("Supabase client initialized successfully")
            else:
                logger.warning("Supabase credentials not found, file storage will use local storage")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
    
    async def validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validate uploaded file format and size"""
        # Check file size
        file_size = len(file_content)
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum allowed size ({settings.MAX_FILE_SIZE} bytes)")
        
        # Detect file type
        file_type = filetype.guess(file_content)
        if not file_type:
            # Try to guess from filename extension
            file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
            if file_extension not in settings.SUPPORTED_AUDIO_FORMATS + settings.SUPPORTED_VIDEO_FORMATS:
                raise ValueError(f"Unsupported file format. Supported formats: {settings.SUPPORTED_AUDIO_FORMATS + settings.SUPPORTED_VIDEO_FORMATS}")
            detected_format = file_extension
            mime_type = self._get_mime_type(file_extension)
        else:
            detected_format = file_type.extension
            mime_type = file_type.mime
            
            # Validate against supported formats
            if detected_format not in settings.SUPPORTED_AUDIO_FORMATS + settings.SUPPORTED_VIDEO_FORMATS:
                raise ValueError(f"Unsupported file format: {detected_format}. Supported formats: {settings.SUPPORTED_AUDIO_FORMATS + settings.SUPPORTED_VIDEO_FORMATS}")
        
        return {
            'filename': filename,
            'file_size': file_size,
            'format': detected_format,
            'mime_type': mime_type,
            'is_valid': True
        }
    
    def _get_mime_type(self, extension: str) -> str:
        """Get MIME type for file extension"""
        mime_types = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'm4a': 'audio/mp4',
            'flac': 'audio/flac',
            'aac': 'audio/aac',
            'ogg': 'audio/ogg',
            'wma': 'audio/x-ms-wma',
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime',
            'mkv': 'video/x-matroska',
            'wmv': 'video/x-ms-wmv',
            'flv': 'video/x-flv',
            'webm': 'video/webm'
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    async def upload_file(self, file_content: bytes, filename: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload file to Supabase Storage"""
        try:
            # Validate file first
            validation_result = await self.validate_file(file_content, filename)
            
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = validation_result['format']
            storage_filename = f"{file_id}.{file_extension}"
            
            # Create file path with user organization
            if user_id:
                file_path = f"users/{user_id}/{storage_filename}"
            else:
                file_path = f"temp/{storage_filename}"
            
            if self.supabase and self.storage_client:
                # Upload to Supabase Storage
                result = self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
                    file_path,
                    file_content,
                    file_options={
                        "content-type": validation_result['mime_type'],
                        "cache-control": "3600"
                    }
                )
                
                if result.status_code == 200:
                    # Get public URL
                    public_url = self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(file_path)
                    
                    logger.info(f"File uploaded successfully to Supabase: {file_path}")
                    
                    return {
                        'file_id': file_id,
                        'storage_path': file_path,
                        'public_url': public_url,
                        'local_path': None,
                        'metadata': FileMetadata(
                            filename=filename,
                            content_type=validation_result['mime_type'],
                            file_size=validation_result['file_size'],
                            format=validation_result['format']
                        )
                    }
                else:
                    raise Exception(f"Failed to upload to Supabase: {result}")
            else:
                # Fallback to local storage
                return await self._upload_local(file_content, filename, validation_result)
                
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise
    
    async def _upload_local(self, file_content: bytes, filename: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback local file upload"""
        # Create upload directory if it doesn't exist
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = validation_result['format']
        storage_filename = f"{file_id}.{file_extension}"
        local_path = os.path.join(upload_dir, storage_filename)
        
        # Write file to local storage
        with open(local_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"File uploaded locally: {local_path}")
        
        return {
            'file_id': file_id,
            'storage_path': None,
            'public_url': None,
            'local_path': local_path,
            'metadata': FileMetadata(
                filename=filename,
                content_type=validation_result['mime_type'],
                file_size=validation_result['file_size'],
                format=validation_result['format']
            )
        }
    
    async def download_file(self, file_path: str) -> bytes:
        """Download file from Supabase Storage"""
        try:
            if self.supabase and file_path:
                # Download from Supabase Storage
                result = self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).download(file_path)
                if result:
                    return result
                else:
                    raise Exception("Failed to download file from Supabase")
            else:
                raise Exception("Supabase client not initialized or invalid file path")
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            raise
    
    async def get_local_file_path(self, file_path: str, file_id: str) -> str:
        """Get local file path for processing (download from Supabase if needed)"""
        try:
            if file_path and self.supabase:
                # Download file from Supabase to temporary location
                file_content = await self.download_file(file_path)
                
                # Create temporary file
                temp_dir = settings.TEMP_DIR
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_file_path = os.path.join(temp_dir, f"{file_id}_temp")
                with open(temp_file_path, 'wb') as f:
                    f.write(file_content)
                
                return temp_file_path
            else:
                # File is already local, return the path
                return file_path
        except Exception as e:
            logger.error(f"Failed to get local file path: {str(e)}")
            raise
    
    async def delete_file(self, file_path: Optional[str] = None, local_path: Optional[str] = None):
        """Delete file from storage"""
        try:
            # Delete from Supabase Storage
            if file_path and self.supabase:
                result = self.supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([file_path])
                if result:
                    logger.info(f"File deleted from Supabase: {file_path}")
                else:
                    logger.warning(f"Failed to delete file from Supabase: {file_path}")
            
            # Delete local file
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Local file deleted: {local_path}")
                
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than specified hours"""
        try:
            temp_dir = settings.TEMP_DIR
            if not os.path.exists(temp_dir):
                return
            
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=max_age_hours)
            
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Cleaned up temp file: {file_path}")
                        
        except Exception as e:
            logger.error(f"Temp file cleanup failed: {str(e)}")
    
    async def get_file_duration(self, file_path: str) -> Optional[float]:
        """Get audio/video file duration using ffprobe (if available)"""
        try:
            import subprocess
            import json
            
            # Use ffprobe to get file duration
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                return duration
            else:
                logger.warning(f"Could not get duration for file: {file_path}")
                return None
                
        except Exception as e:
            logger.warning(f"Duration detection failed: {str(e)}")
            return None

# Global file handler service instance
file_handler = FileHandlerService()