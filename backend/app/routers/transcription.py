from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from typing import Optional, List
import aiofiles
import os
import tempfile
import logging
from app.models.schemas import (
    TaskResponse, ProgressResponse, TranscriptResponse, 
    YouTubeRequest, SupportedLanguage, TaskStatus, SourceType
)
from app.services.auth import get_current_user, get_current_user_optional
from app.services.transcription import transcription_service
from app.config import settings
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=TaskResponse)
async def upload_file(
    file: UploadFile = File(...),
    target_language: Optional[str] = Form(None),
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """Upload audio/video file for transcription"""
    
    # Validate file type
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type could not be determined"
        )
    
    # Check file format
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ""
    supported_formats = settings.SUPPORTED_AUDIO_FORMATS + settings.SUPPORTED_VIDEO_FORMATS
    
    if file_extension not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE_FORMAT",
                "message": f"Unsupported file format: {file_extension}",
                "supported_formats": supported_formats
            }
        )
    
    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File size exceeds limit of {settings.MAX_FILE_SIZE / (1024*1024):.0f}MB",
                "max_size_mb": settings.MAX_FILE_SIZE / (1024*1024)
            }
        )
    
    # Save file temporarily
    temp_file_path = os.path.join(settings.TEMP_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    try:
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(content)
        
        # Create transcription task
        user_id = user.get('uid') if user else None
        task_id = await transcription_service.create_task(
            source_path=temp_file_path,
            source_type=SourceType.FILE,
            user_id=user_id,
            target_language=target_language
        )
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="File uploaded successfully. Transcription started.",
            estimated_duration=file_size / (1024 * 1024) * 2  # Rough estimate: 2 minutes per MB
        )
        
    except Exception as e:
        # Clean up temp file if something goes wrong
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )

@router.post("/youtube", response_model=TaskResponse)
async def process_youtube(
    request: YouTubeRequest,
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """Process YouTube video for transcription"""
    
    try:
        from app.services.youtube import youtube_service
        
        # Validate YouTube URL first
        logger.info(f"Validating YouTube URL: {request.url}")
        validation_result = await youtube_service.validate_youtube_url(request.url)
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_YOUTUBE_URL",
                    "message": f"YouTube URL validation failed: {validation_result['error']}",
                    "url": request.url
                }
            )
        
        logger.info(f"YouTube URL validated successfully: {validation_result['title']}")
        
        # Create transcription task
        user_id = user.get('uid') if user else None
        task_id = await transcription_service.create_task(
            source_path=request.url,
            source_type=SourceType.YOUTUBE,
            user_id=user_id,
            target_language=request.target_language
        )
        
        # Estimate duration based on video length
        video_duration = validation_result.get('duration', 300)
        estimated_processing_time = max(video_duration * 0.5, 60)  # At least 1 minute, roughly half the video duration
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"YouTube video '{validation_result['title']}' processing started.",
            estimated_duration=estimated_processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTube processing failed: {str(e)}"
        )

@router.get("/progress/{task_id}", response_model=ProgressResponse)
async def get_progress(
    task_id: str,
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get transcription progress"""
    
    task = await transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if user owns this task (if authenticated)
    if user and task.user_id and task.user_id != user.get('uid'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ProgressResponse(
        task_id=task_id,
        status=task.status,
        progress=task.progress,
        estimated_time=task.estimated_duration,
        error_message=task.error_message
    )

@router.get("/transcript/{task_id}", response_model=TranscriptResponse)
async def get_transcript(
    task_id: str,
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get completed transcript with translation support"""
    
    task = await transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if user owns this task (if authenticated)
    if user and task.user_id and task.user_id != user.get('uid'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcript not ready. Current status: {task.status}"
        )
    
    # Calculate average confidence from segments if available
    confidence = 0.95  # Default confidence
    if task.segments:
        confidences = [seg.confidence for seg in task.segments if hasattr(seg, 'confidence')]
        if confidences:
            confidence = sum(confidences) / len(confidences)
    
    # Get metadata from task or create default
    metadata = task.metadata or {}
    file_metadata = {
        "filename": os.path.basename(task.source_path),
        "content_type": metadata.get('format_info', {}).get('type', 'audio/mpeg'),
        "file_size": metadata.get('file_size', 0),
        "duration": metadata.get('duration'),
        "format": metadata.get('format_info', {}).get('format', 'unknown')
    }
    
    return TranscriptResponse(
        task_id=task_id,
        text=task.transcript or "",
        source_language=task.source_language or "unknown",
        target_language=task.target_language or task.source_language or "unknown",
        is_translated=getattr(task, 'is_translated', False),
        confidence=confidence,
        metadata=file_metadata,
        segments=task.segments or []
    )

@router.get("/transcript/{task_id}/download")
async def download_transcript(
    task_id: str,
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """Download transcript as text file"""
    
    task = await transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if user owns this task (if authenticated)
    if user and task.user_id and task.user_id != user.get('uid'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    if task.status != TaskStatus.COMPLETED or not task.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript not available"
        )
    
    # Create file-like object for streaming
    def generate_file():
        yield task.transcript.encode('utf-8')
    
    filename = f"transcript_{task_id}.txt"
    
    return StreamingResponse(
        generate_file(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/languages/supported", response_model=List[SupportedLanguage])
async def get_supported_languages():
    """Get list of supported languages"""
    
    languages = await transcription_service.get_supported_languages()
    
    return [
        SupportedLanguage(
            code=lang["code"],
            name=lang["name"],
            native_name=lang["native"],
            whisper_supported=True,
            translation_supported=True
        )
        for lang in languages
    ]

@router.get("/tasks", response_model=List[dict])
async def get_user_tasks(
    user: dict = Depends(get_current_user)
):
    """Get all tasks for authenticated user"""
    
    tasks = await transcription_service.get_user_tasks(user['uid'])
    
    return [
        {
            "id": task.id,
            "status": task.status,
            "progress": task.progress,
            "source_type": task.source_type,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "source_language": task.source_language,
            "target_language": task.target_language
        }
        for task in tasks
    ]