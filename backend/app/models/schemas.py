from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SourceType(str, Enum):
    FILE = "file"
    YOUTUBE = "youtube"
    RECORDING = "recording"

class SubscriptionStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

# Base Models
class SupportedLanguage(BaseModel):
    code: str = Field(..., description="ISO 639-1 language code")
    name: str = Field(..., description="English name of the language")
    native_name: str = Field(..., description="Native name of the language")
    whisper_supported: bool = Field(default=True, description="Supported by Whisper")
    translation_supported: bool = Field(default=True, description="Supported for translation")

class FileMetadata(BaseModel):
    filename: str
    content_type: str
    file_size: int = Field(..., description="File size in bytes")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    format: str

class TranscriptSegment(BaseModel):
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    original_text: Optional[str] = Field(None, description="Original text before translation")
    translation_info: Optional[Dict[str, Any]] = Field(None, description="Translation metadata")

class Transcript(BaseModel):
    text: str
    source_language: str
    target_language: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_translated: bool = Field(default=False)
    segments: List[TranscriptSegment] = Field(default_factory=list)
    metadata: FileMetadata

class TranscriptionTask(BaseModel):
    id: str
    user_id: Optional[str] = None
    status: TaskStatus
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    source_type: SourceType
    source_path: str
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    transcript: Optional[str] = None
    segments: Optional[List[TranscriptSegment]] = Field(default_factory=list)
    is_translated: bool = Field(default=False)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    estimated_duration: Optional[float] = None
    processing_time: Optional[float] = None

# User Management Models
class User(BaseModel):
    id: str  # Firebase UID
    email: str
    display_name: Optional[str] = None
    subscription_id: str
    created_at: datetime
    last_login: datetime
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)

class SubscriptionPlan(BaseModel):
    id: str
    name: str
    description: str
    price_monthly: float = Field(..., ge=0)
    price_yearly: float = Field(..., ge=0)
    max_file_size_mb: int = Field(..., gt=0)
    max_monthly_minutes: int = Field(..., gt=0)
    max_concurrent_tasks: int = Field(..., gt=0)
    features: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)

class Subscription(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    auto_renew: bool = Field(default=True)
    payment_method_id: Optional[str] = None

class UsageRecord(BaseModel):
    id: str
    user_id: str
    task_id: str
    file_size_mb: float = Field(..., ge=0)
    duration_minutes: float = Field(..., ge=0)
    processing_time_seconds: float = Field(..., ge=0)
    source_language: str
    target_language: Optional[str] = None
    is_translation: bool = Field(default=False)
    created_at: datetime
    billing_period: str  # YYYY-MM format

# Request/Response Models
class FileUploadRequest(BaseModel):
    target_language: Optional[str] = Field(None, description="Target language code")

class YouTubeRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    target_language: Optional[str] = Field(None, description="Target language code")
    use_subtitles: bool = Field(default=True, description="Whether to use available subtitles instead of audio transcription")
    prefer_manual_subtitles: bool = Field(default=True, description="Whether to prefer manual subtitles over automatic captions")
    subtitle_language: Optional[str] = Field(None, description="Preferred subtitle language code (defaults to target_language or auto-detect)")
    
    @validator('url')
    def validate_youtube_url(cls, v):
        if not any(domain in v for domain in ['youtube.com', 'youtu.be']):
            raise ValueError('Invalid YouTube URL')
        return v

class TranslationRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    source_language: str = Field(..., description="Source language code")
    target_language: str = Field(..., description="Target language code")
    use_context: bool = Field(default=False, description="Use context-aware translation")
    context: Optional[str] = Field(None, description="Context for translation")

class TranslationResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    service: str = Field(..., description="Translation service used")
    success: bool
    context_aware: bool = Field(default=False)

class LanguageDetectionRequest(BaseModel):
    text: Optional[str] = Field(None, description="Text for language detection")
    audio_path: Optional[str] = Field(None, description="Audio file path for detection")

class LanguageDetectionResponse(BaseModel):
    detected_language: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    sample_text: Optional[str] = None
    method: str = Field(..., description="Detection method used")

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    estimated_duration: Optional[float] = None
    estimated_cost: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ProgressResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: float = Field(..., ge=0.0, le=100.0)
    estimated_time: Optional[float] = None
    error_message: Optional[str] = None
    usage_consumed: Optional[Dict[str, float]] = None

class TranscriptResponse(BaseModel):
    task_id: str
    text: str
    source_language: str
    target_language: str
    is_translated: bool
    confidence: float
    metadata: FileMetadata
    segments: List[TranscriptSegment] = Field(default_factory=list)

class UsageStats(BaseModel):
    current_period: Dict[str, int] = Field(default_factory=dict)
    limits: Dict[str, int] = Field(default_factory=dict)
    remaining: Dict[str, int] = Field(default_factory=dict)

class UserProfile(BaseModel):
    user: User
    subscription: Subscription
    usage: UsageStats

# Admin Models
class SystemStats(BaseModel):
    total_users: int
    active_users: int
    total_transcriptions: int
    monthly_revenue: float
    system_uptime: float
    avg_processing_time: float

class AdminDashboardResponse(BaseModel):
    stats: SystemStats
    recent_activity: List[Dict[str, Any]]
    system_health: List[Dict[str, Any]]

# Error Models
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float

class ErrorResponse(BaseModel):
    error: ErrorDetail