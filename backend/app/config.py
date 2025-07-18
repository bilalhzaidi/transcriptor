from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Audio Video Transcription API"
    VERSION: str = "1.0.0"
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    UPLOAD_DIR: str = "uploads"
    TEMP_DIR: str = "temp"
    
    # Supported file formats
    SUPPORTED_AUDIO_FORMATS: List[str] = [
        "mp3", "wav", "m4a", "flac", "aac", "ogg", "wma"
    ]
    SUPPORTED_VIDEO_FORMATS: List[str] = [
        "mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"
    ]
    
    # Whisper Configuration
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large
    WHISPER_DEVICE: str = "cpu"  # cpu or cuda
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Google Translate Configuration
    GOOGLE_TRANSLATE_PROJECT_ID: str = os.getenv("GOOGLE_TRANSLATE_PROJECT_ID", "")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "transcription-files")
    
    # YouTube Configuration
    YOUTUBE_MAX_DURATION: int = 3600  # 1 hour in seconds
    YOUTUBE_MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    YOUTUBE_AUDIO_FORMAT: str = "mp3"
    YOUTUBE_AUDIO_QUALITY: str = "192"  # kbps
    
    # Task Configuration
    TASK_TIMEOUT: int = 3600  # 1 hour in seconds
    MAX_CONCURRENT_TASKS: int = 5
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()