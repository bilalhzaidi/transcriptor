import whisper
import asyncio
import os
import tempfile
import logging
import subprocess
import json
import time
from typing import Optional, Dict, Any, List, Tuple
from app.models.schemas import TranscriptionTask, TaskStatus, SourceType, TranscriptSegment
from app.config import settings
from app.services.file_handler import file_handler
import uuid
from datetime import datetime
import torch

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.model = None
        self.model_name = settings.WHISPER_MODEL
        self.device = settings.WHISPER_DEVICE
        self.tasks: Dict[str, TranscriptionTask] = {}
        self.model_loading = False
        self.model_load_time = None
        
        # Validate device availability
        self._validate_device()
    
    def _validate_device(self):
        """Validate and set appropriate device for Whisper"""
        if self.device == "cuda":
            if torch.cuda.is_available():
                logger.info(f"CUDA is available. Using GPU for Whisper inference.")
                # Get GPU info
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                logger.info(f"GPU: {gpu_name}, Memory: {gpu_memory:.1f}GB")
            else:
                logger.warning("CUDA requested but not available. Falling back to CPU.")
                self.device = "cpu"
        else:
            logger.info("Using CPU for Whisper inference.")
    
    async def load_model(self):
        """Load Whisper model asynchronously with caching and error handling"""
        if self.model is not None:
            return  # Model already loaded
        
        if self.model_loading:
            # Wait for ongoing model loading
            while self.model_loading:
                await asyncio.sleep(0.1)
            return
        
        self.model_loading = True
        start_time = time.time()
        
        try:
            logger.info(f"Loading Whisper model: {self.model_name} on {self.device}")
            
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                self._load_model_sync
            )
            
            self.model_load_time = time.time() - start_time
            logger.info(f"Whisper model loaded successfully in {self.model_load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise Exception(f"Model loading failed: {str(e)}")
        finally:
            self.model_loading = False
    
    def _load_model_sync(self):
        """Synchronous model loading with error handling"""
        try:
            # Load model with specific device
            model = whisper.load_model(self.model_name, device=self.device)
            
            # Validate model loaded correctly
            if model is None:
                raise Exception("Model loading returned None")
            
            # Test model with a small dummy input if possible
            logger.info(f"Model loaded: {self.model_name}")
            try:
                # Try to get device info if available
                params = list(model.parameters())
                if params:
                    logger.info(f"Model device: {params[0].device}")
            except Exception:
                # Skip device logging if not available (e.g., in tests)
                pass
            
            return model
            
        except Exception as e:
            logger.error(f"Synchronous model loading failed: {str(e)}")
            raise
    
    async def create_task(
        self, 
        source_path: str, 
        source_type: SourceType,
        user_id: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> str:
        """Create a new transcription task"""
        task_id = str(uuid.uuid4())
        
        task = TranscriptionTask(
            id=task_id,
            user_id=user_id,
            status=TaskStatus.PENDING,
            source_type=source_type,
            source_path=source_path,
            target_language=target_language,
            created_at=datetime.utcnow()
        )
        
        self.tasks[task_id] = task
        logger.info(f"Created transcription task: {task_id}")
        
        # Start processing in background
        asyncio.create_task(self._process_task(task_id))
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[TranscriptionTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    async def get_user_tasks(self, user_id: str) -> List[TranscriptionTask]:
        """Get all tasks for a user"""
        return [task for task in self.tasks.values() if task.user_id == user_id]
    
    async def _process_task(self, task_id: str):
        """Process transcription task with enhanced translation workflow"""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return
        
        try:
            # Update task status
            task.status = TaskStatus.PROCESSING
            task.progress = 10.0
            
            # Load model if not already loaded
            await self.load_model()
            task.progress = 20.0
            
            # Handle different source types
            if task.source_type == SourceType.YOUTUBE:
                # Process YouTube video
                logger.info(f"Processing YouTube video for task: {task_id}")
                youtube_result = await self._process_youtube_video(task.source_path, task.metadata)
                if not youtube_result['success']:
                    raise Exception(f"YouTube processing failed: {youtube_result['error']}")
                
                # Update task with YouTube metadata
                task.metadata = youtube_result.get('metadata', {})
                task.progress = 40.0
                
                # Check if we're using subtitles or audio
                if youtube_result.get('from_subtitles', False) and youtube_result.get('subtitle_text'):
                    logger.info(f"Using extracted subtitles for task: {task_id}")
                    
                    # Parse subtitles to create a transcript
                    subtitle_text = youtube_result['subtitle_text']
                    subtitle_language = youtube_result.get('subtitle_language', 'en')
                    subtitle_source = youtube_result.get('subtitle_source', 'unknown')
                    
                    # Process subtitles to create transcript and segments
                    subtitle_result = await self._process_subtitles(subtitle_text, subtitle_language)
                    
                    # Update task with subtitle results
                    task.transcript = subtitle_result['text']
                    task.segments = subtitle_result['segments']
                    task.source_language = subtitle_language
                    task.metadata['subtitle_source'] = subtitle_source
                    task.metadata['from_subtitles'] = True
                    task.progress = 70.0
                    
                    # No need to transcribe audio
                    result = {
                        'text': subtitle_result['text'],
                        'language': subtitle_language,
                        'segments': subtitle_result['segments'],
                        'metadata': {
                            'from_subtitles': True,
                            'subtitle_source': subtitle_source
                        }
                    }
                else:
                    # Transcribe the downloaded audio
                    logger.info(f"Transcribing downloaded audio for task: {task_id}")
                    result = await self._transcribe_audio(youtube_result['file_path'], task.target_language)
                    
                    # Clean up downloaded audio file
                    await self._cleanup_temp_file(youtube_result['file_path'])
            else:
                # Process regular file
                logger.info(f"Starting transcription for task: {task_id}")
                result = await self._transcribe_audio(task.source_path, task.target_language)
            
            # Update task with initial results
            task.source_language = result['language']
            task.progress = 70.0
            
            # Check if translation is needed
            needs_translation = (
                task.target_language and 
                task.target_language != result['language'] and
                task.target_language != 'auto'
            )
            
            if needs_translation:
                logger.info(f"Translation needed: {result['language']} -> {task.target_language}")
                task.progress = 75.0
                
                # Translate segments for better quality
                if result.get('segments'):
                    logger.info(f"Translating {len(result['segments'])} segments")
                    translated_segments = await self._translate_segments(
                        result['segments'], 
                        result['language'], 
                        task.target_language
                    )
                    
                    # Reconstruct full text from translated segments
                    task.transcript = ' '.join([seg.get('text', '') for seg in translated_segments if seg.get('text', '').strip()])
                    task.segments = translated_segments
                    task.progress = 95.0
                else:
                    # Fallback to full text translation
                    logger.info("No segments available, translating full text")
                    task.transcript = await self._translate_text(
                        result['text'], 
                        result['language'], 
                        task.target_language
                    )
                    task.progress = 95.0
                
                # Mark as translated
                task.is_translated = True
                logger.info(f"Translation completed: {result['language']} -> {task.target_language}")
            else:
                # No translation needed
                task.transcript = result['text']
                task.segments = result.get('segments', [])
                task.is_translated = False
                task.progress = 95.0
            
            # Store additional metadata
            task.metadata = {
                'duration': result.get('metadata', {}).get('duration'),
                'file_size': result.get('metadata', {}).get('file_size'),
                'format_info': result.get('metadata', {}).get('format_info'),
                'processing_time': None,  # Could be calculated
                'model_used': self.model_name,
                'device_used': self.device
            }
            
            # Complete task
            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.completed_at = datetime.utcnow()
            
            logger.info(f"Transcription task completed: {task_id} (translated: {task.is_translated})")
            
        except Exception as e:
            logger.error(f"Transcription failed for task {task_id}: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.progress = 0.0
    
    async def validate_audio_format(self, file_path: str) -> Dict[str, Any]:
        """Validate audio/video file format for transcription compatibility"""
        try:
            # Get file extension
            file_extension = os.path.splitext(file_path)[1].lower().lstrip('.')
            
            # Check if format is supported
            supported_formats = settings.SUPPORTED_AUDIO_FORMATS + settings.SUPPORTED_VIDEO_FORMATS
            
            if file_extension not in supported_formats:
                raise ValueError(f"Unsupported format: {file_extension}. Supported formats: {supported_formats}")
            
            # Determine if it's audio or video
            format_type = "audio" if file_extension in settings.SUPPORTED_AUDIO_FORMATS else "video"
            
            return {
                'format': file_extension,
                'type': format_type,
                'supported': True,
                'whisper_compatible': True  # Whisper can handle most formats via ffmpeg
            }
            
        except Exception as e:
            logger.error(f"Format validation failed: {str(e)}")
            raise
    
    async def preprocess_audio(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Preprocess audio file for transcription with enhanced format support"""
        try:
            # Validate format first
            format_info = await self.validate_audio_format(file_path)
            
            # Get file duration and metadata
            duration = await file_handler.get_file_duration(file_path)
            
            # Get file info
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            metadata = {
                'duration': duration,
                'file_size': file_size,
                'original_path': file_path,
                'format_info': format_info,
                'preprocessing_applied': []
            }
            
            # Apply preprocessing based on file characteristics
            processed_path = file_path
            
            # For large files, we might want to split them
            if duration and duration > 3600:  # 1 hour
                logger.warning(f"Large file detected ({duration}s). Consider splitting for better performance.")
                metadata['preprocessing_applied'].append('large_file_warning')
            
            # For video files, note that audio will be extracted automatically by Whisper
            if format_info['type'] == 'video':
                logger.info(f"Video file detected. Whisper will extract audio automatically.")
                metadata['preprocessing_applied'].append('video_audio_extraction')
            
            logger.info(f"Audio preprocessing completed: {duration}s duration, {file_size} bytes, format: {format_info['format']}")
            return processed_path, metadata
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {str(e)}")
            raise Exception(f"Audio preprocessing failed: {str(e)}")
    
    async def _transcribe_audio(self, audio_path: str, target_language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio file using Whisper with preprocessing"""
        try:
            # Preprocess audio
            processed_path, metadata = await self.preprocess_audio(audio_path)
            
            loop = asyncio.get_event_loop()
            
            def _transcribe():
                try:
                    # Configure transcription options
                    transcribe_options = {
                        'task': 'transcribe',
                        'verbose': False,
                        'word_timestamps': True,  # Enable word-level timestamps
                    }
                    
                    # Add language if specified
                    if target_language and len(target_language) == 2:
                        transcribe_options['language'] = target_language
                    
                    # Transcribe with Whisper
                    result = self.model.transcribe(processed_path, **transcribe_options)
                    
                    # Process segments with confidence scores
                    segments = []
                    for segment in result.get('segments', []):
                        segments.append({
                            'start': segment.get('start', 0.0),
                            'end': segment.get('end', 0.0),
                            'text': segment.get('text', '').strip(),
                            'confidence': segment.get('avg_logprob', 0.0)  # Use avg_logprob as confidence
                        })
                    
                    return {
                        'text': result['text'].strip(),
                        'language': result.get('language', 'unknown'),
                        'segments': segments,
                        'metadata': metadata
                    }
                    
                except Exception as e:
                    logger.error(f"Whisper transcription error: {str(e)}")
                    raise
            
            return await loop.run_in_executor(None, _transcribe)
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise
    
    async def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text using translation service"""
        try:
            from app.services.translation import translation_service
            
            logger.info(f"Translation requested: {source_lang} -> {target_lang}")
            
            # Use translation service with context
            result = await translation_service.translate_text(
                text=text,
                source_language=source_lang,
                target_language=target_lang,
                context="audio transcription content"
            )
            
            if result.get('error'):
                logger.warning(f"Translation failed: {result.get('error', 'Unknown error')}")
                return text  # Return original text on failure
            
            logger.info(f"Translation completed using {result['provider']}")
            return result['translated_text']
            
        except Exception as e:
            logger.error(f"Translation service error: {str(e)}")
            return text  # Return original text on failure
    
    async def _translate_segments(self, segments: List[Dict[str, Any]], source_lang: str, target_lang: str) -> List[Dict[str, Any]]:
        """Translate transcript segments using translation service"""
        try:
            from app.services.translation import translation_service
            
            logger.info(f"Segment translation requested: {source_lang} -> {target_lang} for {len(segments)} segments")
            
            translated_segments = []
            
            # Translate each segment individually
            for segment in segments:
                text = segment.get('text', '').strip()
                if not text:
                    # Keep empty segments as-is
                    translated_segments.append(segment)
                    continue
                
                # Translate the segment text
                result = await translation_service.translate_text(
                    text=text,
                    source_language=source_lang,
                    target_language=target_lang,
                    context="audio transcription segment"
                )
                
                # Create translated segment
                translated_segment = segment.copy()
                if not result.get('error'):
                    translated_segment['text'] = result['translated_text']
                    translated_segment['original_text'] = text
                    translated_segment['translation_info'] = {
                        'service': result['provider'],
                        'source_language': source_lang,
                        'target_language': target_lang,
                        'confidence': result.get('confidence', 0.0)
                    }
                else:
                    # Keep original text if translation failed
                    logger.warning(f"Translation failed for segment: {result.get('error')}")
                    translated_segment['original_text'] = text
                
                translated_segments.append(translated_segment)
            
            logger.info(f"Segment translation completed for {len(translated_segments)} segments")
            return translated_segments
            
        except Exception as e:
            logger.error(f"Segment translation error: {str(e)}")
            # Return original segments on failure
            return segments
    
    async def _process_youtube_video(self, youtube_url: str, task_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process YouTube video and extract audio or subtitles for transcription"""
        try:
            from app.services.youtube import youtube_service
            
            logger.info(f"Processing YouTube video: {youtube_url}")
            task_metadata = task_metadata or {}
            
            # Validate YouTube URL first
            validation_result = await youtube_service.validate_youtube_url(youtube_url)
            if not validation_result['valid']:
                raise Exception(f"Invalid YouTube URL: {validation_result['error']}")
            
            logger.info(f"YouTube video validated: {validation_result['title']}")
            
            # Check if we should use subtitles
            use_subtitles = task_metadata.get('use_subtitles', False)
            subtitle_language = task_metadata.get('subtitle_language')
            prefer_manual = task_metadata.get('prefer_manual_subtitles', True)
            
            if use_subtitles:
                logger.info(f"Attempting to use YouTube subtitles for {youtube_url}")
                
                # Get video metadata to check available subtitles
                metadata_result = await youtube_service.get_video_metadata(youtube_url)
                if not metadata_result['success']:
                    logger.warning(f"Failed to get video metadata: {metadata_result.get('error')}")
                    use_subtitles = False  # Fall back to audio transcription
                else:
                    metadata = metadata_result['metadata']
                    manual_subtitles = metadata.get('subtitles', [])
                    auto_captions = metadata.get('automatic_captions', [])
                    
                    # Determine which subtitle language to use
                    target_lang = subtitle_language or task_metadata.get('target_language') or 'en'
                    
                    # Check if preferred language is available
                    has_manual = target_lang in manual_subtitles
                    has_auto = target_lang in auto_captions
                    
                    if (has_manual and prefer_manual) or (has_manual and not has_auto):
                        # Use manual subtitles
                        logger.info(f"Using manual subtitles in {target_lang} for {youtube_url}")
                        subtitle_result = await youtube_service.extract_subtitles(youtube_url, target_lang)
                        
                        if subtitle_result['success'] and subtitle_result['subtitles']:
                            logger.info(f"Successfully extracted manual subtitles")
                            return {
                                'success': True,
                                'subtitle_text': subtitle_result['subtitles'],
                                'from_subtitles': True,
                                'subtitle_language': subtitle_result['language'],
                                'subtitle_source': 'manual',
                                'metadata': {
                                    'youtube_title': validation_result['title'],
                                    'youtube_video_id': validation_result['video_id'],
                                    'duration': validation_result['duration'],
                                    'original_url': youtube_url,
                                    'uploader': validation_result.get('uploader'),
                                    'from_subtitles': True
                                }
                            }
                        else:
                            logger.warning(f"Failed to extract manual subtitles: {subtitle_result.get('error')}")
                    
                    elif has_auto:
                        # Use automatic captions
                        logger.info(f"Using automatic captions in {target_lang} for {youtube_url}")
                        subtitle_result = await youtube_service.extract_subtitles(youtube_url, target_lang)
                        
                        if subtitle_result['success'] and subtitle_result['subtitles']:
                            logger.info(f"Successfully extracted automatic captions")
                            return {
                                'success': True,
                                'subtitle_text': subtitle_result['subtitles'],
                                'from_subtitles': True,
                                'subtitle_language': subtitle_result['language'],
                                'subtitle_source': 'automatic',
                                'metadata': {
                                    'youtube_title': validation_result['title'],
                                    'youtube_video_id': validation_result['video_id'],
                                    'duration': validation_result['duration'],
                                    'original_url': youtube_url,
                                    'uploader': validation_result.get('uploader'),
                                    'from_subtitles': True
                                }
                            }
                        else:
                            logger.warning(f"Failed to extract automatic captions: {subtitle_result.get('error')}")
                    
                    else:
                        logger.info(f"No subtitles available in {target_lang}, falling back to audio transcription")
                        use_subtitles = False  # Fall back to audio transcription
            
            # If subtitles weren't used or failed, fall back to audio transcription
            if not use_subtitles:
                logger.info(f"Using audio transcription for {youtube_url}")
                
                # Download audio from YouTube video
                download_result = await youtube_service.download_audio(youtube_url)
                if not download_result['success']:
                    raise Exception(f"Failed to download audio: {download_result['error']}")
                
                logger.info(f"YouTube audio downloaded: {download_result['file_path']}")
                
                return {
                    'success': True,
                    'file_path': download_result['file_path'],
                    'from_subtitles': False,
                    'metadata': {
                        'youtube_title': download_result['title'],
                        'youtube_video_id': download_result['video_id'],
                        'duration': download_result['duration'],
                        'file_size': download_result['file_size'],
                        'format': download_result['format'],
                        'original_url': youtube_url,
                        'uploader': download_result['metadata'].get('uploader'),
                        'upload_date': download_result['metadata'].get('upload_date'),
                        'view_count': download_result['metadata'].get('view_count'),
                        'from_subtitles': False
                    }
                }
            
        except Exception as e:
            logger.error(f"YouTube video processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _cleanup_temp_file(self, file_path: str):
        """Clean up temporary files"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")
    
    async def detect_language(self, audio_path: str, duration_limit: float = 30.0) -> Dict[str, Any]:
        """Detect language from audio file using Whisper"""
        try:
            await self.load_model()
            
            loop = asyncio.get_event_loop()
            
            def _detect():
                try:
                    # Use a shorter segment for language detection to save time
                    detect_options = {
                        'task': 'transcribe',
                        'verbose': False,
                        'language': None,  # Let Whisper detect
                        'condition_on_previous_text': False,
                        'temperature': 0.0,  # Use deterministic decoding
                    }
                    
                    # For language detection, we only need a small sample
                    # Whisper will automatically detect language from the first 30 seconds
                    result = self.model.transcribe(audio_path, **detect_options)
                    
                    # Extract language information
                    detected_language = result.get('language', 'unknown')
                    
                    # Calculate confidence based on the first few segments
                    segments = result.get('segments', [])
                    if segments:
                        # Average confidence from first few segments
                        confidence_scores = [seg.get('avg_logprob', -1.0) for seg in segments[:3]]
                        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else -1.0
                        # Convert log probability to a more intuitive confidence score (0-1)
                        confidence = max(0.0, min(1.0, (avg_confidence + 1.0)))
                    else:
                        confidence = 0.0
                    
                    return {
                        'language': detected_language,
                        'confidence': confidence,
                        'sample_text': result['text'][:200] + '...' if len(result['text']) > 200 else result['text'],
                        'segments_analyzed': len(segments)
                    }
                    
                except Exception as e:
                    logger.error(f"Language detection error: {str(e)}")
                    raise
            
            return await loop.run_in_executor(None, _detect)
            
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            raise Exception(f"Language detection failed: {str(e)}")
    
    async def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get comprehensive list of supported languages with Whisper support info"""
        # Whisper officially supports these languages
        whisper_languages = [
            {"code": "en", "name": "English", "native": "English", "whisper_supported": True},
            {"code": "zh", "name": "Chinese", "native": "中文", "whisper_supported": True},
            {"code": "de", "name": "German", "native": "Deutsch", "whisper_supported": True},
            {"code": "es", "name": "Spanish", "native": "Español", "whisper_supported": True},
            {"code": "ru", "name": "Russian", "native": "Русский", "whisper_supported": True},
            {"code": "ko", "name": "Korean", "native": "한국어", "whisper_supported": True},
            {"code": "fr", "name": "French", "native": "Français", "whisper_supported": True},
            {"code": "ja", "name": "Japanese", "native": "日本語", "whisper_supported": True},
            {"code": "pt", "name": "Portuguese", "native": "Português", "whisper_supported": True},
            {"code": "tr", "name": "Turkish", "native": "Türkçe", "whisper_supported": True},
            {"code": "pl", "name": "Polish", "native": "Polski", "whisper_supported": True},
            {"code": "ca", "name": "Catalan", "native": "Català", "whisper_supported": True},
            {"code": "nl", "name": "Dutch", "native": "Nederlands", "whisper_supported": True},
            {"code": "ar", "name": "Arabic", "native": "العربية", "whisper_supported": True},
            {"code": "sv", "name": "Swedish", "native": "Svenska", "whisper_supported": True},
            {"code": "it", "name": "Italian", "native": "Italiano", "whisper_supported": True},
            {"code": "id", "name": "Indonesian", "native": "Bahasa Indonesia", "whisper_supported": True},
            {"code": "hi", "name": "Hindi", "native": "हिन्दी", "whisper_supported": True},
            {"code": "fi", "name": "Finnish", "native": "Suomi", "whisper_supported": True},
            {"code": "vi", "name": "Vietnamese", "native": "Tiếng Việt", "whisper_supported": True},
            {"code": "he", "name": "Hebrew", "native": "עברית", "whisper_supported": True},
            {"code": "uk", "name": "Ukrainian", "native": "Українська", "whisper_supported": True},
            {"code": "el", "name": "Greek", "native": "Ελληνικά", "whisper_supported": True},
            {"code": "ms", "name": "Malay", "native": "Bahasa Melayu", "whisper_supported": True},
            {"code": "cs", "name": "Czech", "native": "Čeština", "whisper_supported": True},
            {"code": "ro", "name": "Romanian", "native": "Română", "whisper_supported": True},
            {"code": "da", "name": "Danish", "native": "Dansk", "whisper_supported": True},
            {"code": "hu", "name": "Hungarian", "native": "Magyar", "whisper_supported": True},
            {"code": "ta", "name": "Tamil", "native": "தமிழ்", "whisper_supported": True},
            {"code": "no", "name": "Norwegian", "native": "Norsk", "whisper_supported": True},
            {"code": "th", "name": "Thai", "native": "ไทย", "whisper_supported": True},
            {"code": "ur", "name": "Urdu", "native": "اردو", "whisper_supported": True},
            {"code": "hr", "name": "Croatian", "native": "Hrvatski", "whisper_supported": True},
            {"code": "bg", "name": "Bulgarian", "native": "Български", "whisper_supported": True},
            {"code": "lt", "name": "Lithuanian", "native": "Lietuvių", "whisper_supported": True},
            {"code": "la", "name": "Latin", "native": "Latina", "whisper_supported": True},
            {"code": "mi", "name": "Maori", "native": "Te Reo Māori", "whisper_supported": True},
            {"code": "ml", "name": "Malayalam", "native": "മലയാളം", "whisper_supported": True},
            {"code": "cy", "name": "Welsh", "native": "Cymraeg", "whisper_supported": True},
            {"code": "sk", "name": "Slovak", "native": "Slovenčina", "whisper_supported": True},
            {"code": "te", "name": "Telugu", "native": "తెలుగు", "whisper_supported": True},
            {"code": "fa", "name": "Persian", "native": "فارسی", "whisper_supported": True},
            {"code": "lv", "name": "Latvian", "native": "Latviešu", "whisper_supported": True},
            {"code": "bn", "name": "Bengali", "native": "বাংলা", "whisper_supported": True},
            {"code": "sr", "name": "Serbian", "native": "Српски", "whisper_supported": True},
            {"code": "az", "name": "Azerbaijani", "native": "Azərbaycan", "whisper_supported": True},
            {"code": "sl", "name": "Slovenian", "native": "Slovenščina", "whisper_supported": True},
            {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ", "whisper_supported": True},
            {"code": "et", "name": "Estonian", "native": "Eesti", "whisper_supported": True},
            {"code": "mk", "name": "Macedonian", "native": "Македонски", "whisper_supported": True},
            {"code": "br", "name": "Breton", "native": "Brezhoneg", "whisper_supported": True},
            {"code": "eu", "name": "Basque", "native": "Euskera", "whisper_supported": True},
            {"code": "is", "name": "Icelandic", "native": "Íslenska", "whisper_supported": True},
            {"code": "hy", "name": "Armenian", "native": "Հայերեն", "whisper_supported": True},
            {"code": "ne", "name": "Nepali", "native": "नेपाली", "whisper_supported": True},
            {"code": "mn", "name": "Mongolian", "native": "Монгол", "whisper_supported": True},
            {"code": "bs", "name": "Bosnian", "native": "Bosanski", "whisper_supported": True},
            {"code": "kk", "name": "Kazakh", "native": "Қазақша", "whisper_supported": True},
            {"code": "sq", "name": "Albanian", "native": "Shqip", "whisper_supported": True},
            {"code": "sw", "name": "Swahili", "native": "Kiswahili", "whisper_supported": True},
            {"code": "gl", "name": "Galician", "native": "Galego", "whisper_supported": True},
            {"code": "mr", "name": "Marathi", "native": "मराठी", "whisper_supported": True},
            {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ", "whisper_supported": True},
            {"code": "si", "name": "Sinhala", "native": "සිංහල", "whisper_supported": True},
            {"code": "km", "name": "Khmer", "native": "ខ្មែរ", "whisper_supported": True},
            {"code": "sn", "name": "Shona", "native": "ChiShona", "whisper_supported": True},
            {"code": "yo", "name": "Yoruba", "native": "Yorùbá", "whisper_supported": True},
            {"code": "so", "name": "Somali", "native": "Soomaali", "whisper_supported": True},
            {"code": "af", "name": "Afrikaans", "native": "Afrikaans", "whisper_supported": True},
            {"code": "oc", "name": "Occitan", "native": "Occitan", "whisper_supported": True},
            {"code": "ka", "name": "Georgian", "native": "ქართული", "whisper_supported": True},
            {"code": "be", "name": "Belarusian", "native": "Беларуская", "whisper_supported": True},
            {"code": "tg", "name": "Tajik", "native": "Тоҷикӣ", "whisper_supported": True},
            {"code": "sd", "name": "Sindhi", "native": "سنڌي", "whisper_supported": True},
            {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી", "whisper_supported": True},
            {"code": "am", "name": "Amharic", "native": "አማርኛ", "whisper_supported": True},
            {"code": "yi", "name": "Yiddish", "native": "ייִדיש", "whisper_supported": True},
            {"code": "lo", "name": "Lao", "native": "ລາວ", "whisper_supported": True},
            {"code": "uz", "name": "Uzbek", "native": "O'zbek", "whisper_supported": True},
            {"code": "fo", "name": "Faroese", "native": "Føroyskt", "whisper_supported": True},
            {"code": "ht", "name": "Haitian Creole", "native": "Kreyòl Ayisyen", "whisper_supported": True},
            {"code": "ps", "name": "Pashto", "native": "پښتو", "whisper_supported": True},
            {"code": "tk", "name": "Turkmen", "native": "Türkmen", "whisper_supported": True},
            {"code": "nn", "name": "Nynorsk", "native": "Nynorsk", "whisper_supported": True},
            {"code": "mt", "name": "Maltese", "native": "Malti", "whisper_supported": True},
            {"code": "sa", "name": "Sanskrit", "native": "संस्कृतम्", "whisper_supported": True},
            {"code": "lb", "name": "Luxembourgish", "native": "Lëtzebuergesch", "whisper_supported": True},
            {"code": "my", "name": "Myanmar", "native": "မြန်မာ", "whisper_supported": True},
            {"code": "bo", "name": "Tibetan", "native": "བོད་ཡིག", "whisper_supported": True},
            {"code": "tl", "name": "Tagalog", "native": "Tagalog", "whisper_supported": True},
            {"code": "mg", "name": "Malagasy", "native": "Malagasy", "whisper_supported": True},
            {"code": "as", "name": "Assamese", "native": "অসমীয়া", "whisper_supported": True},
            {"code": "tt", "name": "Tatar", "native": "Татар", "whisper_supported": True},
            {"code": "haw", "name": "Hawaiian", "native": "ʻŌlelo Hawaiʻi", "whisper_supported": True},
            {"code": "ln", "name": "Lingala", "native": "Lingála", "whisper_supported": True},
            {"code": "ha", "name": "Hausa", "native": "Hausa", "whisper_supported": True},
            {"code": "ba", "name": "Bashkir", "native": "Башҡорт", "whisper_supported": True},
            {"code": "jw", "name": "Javanese", "native": "Basa Jawa", "whisper_supported": True},
            {"code": "su", "name": "Sundanese", "native": "Basa Sunda", "whisper_supported": True},
        ]
        
        return whisper_languages
    
    async def _process_subtitles(self, subtitle_text: str, language: str) -> Dict[str, Any]:
        """Process subtitle text to create transcript and segments"""
        try:
            import re
            from datetime import timedelta
            
            logger.info(f"Processing subtitles in {language}")
            
            # Parse WebVTT format
            # Example format:
            # WEBVTT
            # 
            # 00:00:00.000 --> 00:00:02.000
            # Hello world
            # 
            # 00:00:02.000 --> 00:00:04.000
            # This is a test
            
            # Regular expression to match timestamp lines
            timestamp_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})'
            
            lines = subtitle_text.strip().split('\n')
            segments = []
            current_segment = None
            full_text = []
            
            for line in lines:
                # Skip WEBVTT header and empty lines
                if line == 'WEBVTT' or not line.strip():
                    continue
                
                # Check if this is a timestamp line
                timestamp_match = re.match(timestamp_pattern, line)
                if timestamp_match:
                    # If we have a previous segment, add it to the list
                    if current_segment and current_segment.get('text'):
                        segments.append(current_segment)
                    
                    # Parse timestamps
                    start_time = self._parse_timestamp(timestamp_match.group(1))
                    end_time = self._parse_timestamp(timestamp_match.group(2))
                    
                    # Create new segment
                    current_segment = {
                        'start': start_time,
                        'end': end_time,
                        'text': '',
                        'confidence': 0.95  # Default confidence for subtitles
                    }
                elif current_segment is not None:
                    # Add text to current segment
                    if current_segment['text']:
                        current_segment['text'] += ' ' + line.strip()
                    else:
                        current_segment['text'] = line.strip()
            
            # Add the last segment if it exists
            if current_segment and current_segment.get('text'):
                segments.append(current_segment)
            
            # Create full transcript from segments
            for segment in segments:
                full_text.append(segment['text'])
            
            full_transcript = ' '.join(full_text)
            
            logger.info(f"Processed {len(segments)} subtitle segments")
            
            return {
                'text': full_transcript,
                'segments': segments,
                'language': language
            }
            
        except Exception as e:
            logger.error(f"Subtitle processing failed: {str(e)}")
            # Return empty result on failure
            return {
                'text': '',
                'segments': [],
                'language': language
            }
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Convert WebVTT timestamp to seconds"""
        try:
            hours, minutes, seconds = timestamp.split(':')
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            return total_seconds
        except Exception as e:
            logger.error(f"Failed to parse timestamp {timestamp}: {str(e)}")
            return 0.0

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        current_time = datetime.utcnow()
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            if task.completed_at:
                age_hours = (current_time - task.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.info(f"Cleaned up old task: {task_id}")

# Global transcription service instance
transcription_service = TranscriptionService()