from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
from app.models.schemas import (
    TranslationRequest, 
    TranslationResponse, 
    LanguageDetectionRequest,
    LanguageDetectionResponse,
    SupportedLanguage,
    ErrorResponse
)
from app.services.translation import translation_service
from app.services.transcription import transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/translation", tags=["translation"])

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Translate text using the translation service"""
    try:
        logger.info(f"Translation request: {request.source_language} -> {request.target_language}")
        
        # Validate language codes
        if request.source_language == request.target_language:
            raise HTTPException(
                status_code=400, 
                detail="Source and target languages cannot be the same"
            )
        
        # Perform translation
        result = await translation_service.translate_text(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            context=request.context if request.use_context else None
        )
        
        if result.get('error'):
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {result.get('error', 'Unknown error')}"
            )
        
        return TranslationResponse(
            translated_text=result['translated_text'],
            source_language=result['source_language'],
            target_language=result['target_language'],
            service=result['provider'],
            success=result.get('error') is None,
            context_aware=request.use_context and request.context is not None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@router.post("/detect-language", response_model=LanguageDetectionResponse)
async def detect_language(request: LanguageDetectionRequest):
    """Detect language from text or audio file"""
    try:
        if request.text:
            # Text-based language detection (simplified - in production you'd use a proper library)
            # For now, we'll use a basic approach or integrate with translation service
            logger.info("Text-based language detection requested")
            
            # This is a simplified implementation - in production you'd use langdetect or similar
            detected_lang = "en"  # Default fallback
            confidence = 0.5
            
            return LanguageDetectionResponse(
                detected_language=detected_lang,
                confidence=confidence,
                sample_text=request.text[:100] + "..." if len(request.text) > 100 else request.text,
                method="text_analysis"
            )
            
        elif request.audio_path:
            # Audio-based language detection using Whisper
            logger.info(f"Audio-based language detection for: {request.audio_path}")
            
            result = await transcription_service.detect_language(request.audio_path)
            
            return LanguageDetectionResponse(
                detected_language=result['language'],
                confidence=result['confidence'],
                sample_text=result.get('sample_text'),
                method="whisper_audio_analysis"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either text or audio_path must be provided"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Language detection error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Language detection failed: {str(e)}")

@router.get("/languages/supported", response_model=List[SupportedLanguage])
async def get_supported_languages():
    """Get list of supported languages for translation and transcription"""
    try:
        # Get languages from both services
        transcription_languages = await transcription_service.get_supported_languages()
        translation_languages = await translation_service.get_supported_languages()
        
        # Create a comprehensive list combining both services
        language_map = {}
        
        # Add transcription languages
        for lang in transcription_languages:
            language_map[lang['code']] = {
                'code': lang['code'],
                'name': lang['name'],
                'native_name': lang.get('native', lang['name']),
                'whisper_supported': True,
                'translation_supported': False
            }
        
        # Add translation languages and mark translation support
        for lang in translation_languages:
            code = lang['code']
            if code in language_map:
                language_map[code]['translation_supported'] = True
            else:
                language_map[code] = {
                    'code': code,
                    'name': lang['name'],
                    'native_name': lang.get('native', lang['name']),
                    'whisper_supported': False,
                    'translation_supported': True
                }
        
        # Convert to list of SupportedLanguage objects
        supported_languages = [
            SupportedLanguage(**lang_data) 
            for lang_data in language_map.values()
        ]
        
        # Sort by name for better UX
        supported_languages.sort(key=lambda x: x.name)
        
        logger.info(f"Returning {len(supported_languages)} supported languages")
        return supported_languages
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported languages: {str(e)}")

@router.get("/languages/transcription", response_model=List[Dict[str, Any]])
async def get_transcription_languages():
    """Get languages supported for transcription (Whisper)"""
    try:
        languages = await transcription_service.get_supported_languages()
        logger.info(f"Returning {len(languages)} transcription languages")
        return languages
        
    except Exception as e:
        logger.error(f"Error getting transcription languages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcription languages: {str(e)}")

@router.get("/languages/translation", response_model=List[Dict[str, Any]])
async def get_translation_languages():
    """Get languages supported for translation"""
    try:
        languages = await translation_service.get_supported_languages()
        logger.info(f"Returning {len(languages)} translation languages")
        return languages
        
    except Exception as e:
        logger.error(f"Error getting translation languages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get translation languages: {str(e)}")

@router.get("/health")
async def translation_health_check():
    """Health check for translation services"""
    try:
        health_status = {
            "translation_service": "unknown",
            "google_translate": False,
            "openai": False,
            "whisper_language_detection": False
        }
        
        # Check translation service availability
        try:
            if translation_service.google_client:
                health_status["google_translate"] = True
            if translation_service.openai_client:
                health_status["openai"] = True
            
            if health_status["google_translate"] or health_status["openai"]:
                health_status["translation_service"] = "available"
            else:
                health_status["translation_service"] = "unavailable"
                
        except Exception as e:
            logger.warning(f"Translation service health check failed: {str(e)}")
            health_status["translation_service"] = "error"
        
        # Check Whisper availability for language detection
        try:
            if transcription_service.model or not transcription_service.model_loading:
                health_status["whisper_language_detection"] = True
        except Exception as e:
            logger.warning(f"Whisper health check failed: {str(e)}")
        
        return {
            "status": "healthy" if health_status["translation_service"] == "available" else "degraded",
            "services": health_status,
            "timestamp": logger.time() if hasattr(logger, 'time') else None
        }
        
    except Exception as e:
        logger.error(f"Translation health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": None
        }