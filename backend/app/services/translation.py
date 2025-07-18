import asyncio
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from app.config import settings
import json

# Optional imports for translation providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    translate = None

logger = logging.getLogger(__name__)

class TranslationProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    AUTO = "auto"  # Automatically choose best provider

class TranslationService:
    def __init__(self):
        self.openai_client = None
        self.google_client = None
        self.preferred_provider = TranslationProvider.AUTO
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize translation service clients"""
        # Initialize OpenAI client
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI translation client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
        elif not OPENAI_AVAILABLE:
            logger.info("OpenAI not available (package not installed)")
        
        # Initialize Google Translate client
        if GOOGLE_TRANSLATE_AVAILABLE and settings.GOOGLE_TRANSLATE_PROJECT_ID:
            try:
                self.google_client = translate.Client()
                logger.info("Google Translate client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Translate client: {str(e)}")
        elif not GOOGLE_TRANSLATE_AVAILABLE:
            logger.info("Google Translate not available (package not installed)")
        
        # Set preferred provider based on availability
        if self.openai_client and self.google_client:
            self.preferred_provider = TranslationProvider.OPENAI  # Prefer OpenAI for quality
        elif self.openai_client:
            self.preferred_provider = TranslationProvider.OPENAI
        elif self.google_client:
            self.preferred_provider = TranslationProvider.GOOGLE
        else:
            logger.warning("No translation providers available")
    
    async def translate_text(
        self, 
        text: str, 
        source_language: str, 
        target_language: str,
        provider: Optional[TranslationProvider] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate text from source language to target language
        
        Args:
            text: Text to translate
            source_language: Source language code (ISO 639-1)
            target_language: Target language code (ISO 639-1)
            provider: Translation provider to use (optional)
            context: Additional context for better translation (optional)
        
        Returns:
            Dictionary with translation result and metadata
        """
        if not text or not text.strip():
            return {
                'translated_text': text,
                'source_language': source_language,
                'target_language': target_language,
                'provider': 'none',
                'confidence': 1.0,
                'error': None
            }
        
        # Skip translation if source and target are the same
        if source_language == target_language:
            return {
                'translated_text': text,
                'source_language': source_language,
                'target_language': target_language,
                'provider': 'none',
                'confidence': 1.0,
                'error': None
            }
        
        # Choose provider
        chosen_provider = provider or self.preferred_provider
        
        try:
            if chosen_provider == TranslationProvider.OPENAI and self.openai_client:
                return await self._translate_with_openai(text, source_language, target_language, context)
            elif chosen_provider == TranslationProvider.GOOGLE and self.google_client:
                return await self._translate_with_google(text, source_language, target_language)
            elif chosen_provider == TranslationProvider.AUTO:
                # Try OpenAI first, fallback to Google
                if self.openai_client:
                    try:
                        return await self._translate_with_openai(text, source_language, target_language, context)
                    except Exception as e:
                        logger.warning(f"OpenAI translation failed, trying Google: {str(e)}")
                        if self.google_client:
                            return await self._translate_with_google(text, source_language, target_language)
                        raise
                elif self.google_client:
                    return await self._translate_with_google(text, source_language, target_language)
                else:
                    raise Exception("No translation providers available")
            else:
                raise Exception(f"Translation provider {chosen_provider} not available")
                
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return {
                'translated_text': text,  # Return original text on failure
                'source_language': source_language,
                'target_language': target_language,
                'provider': str(chosen_provider),
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def _translate_with_openai(
        self, 
        text: str, 
        source_language: str, 
        target_language: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Translate text using OpenAI GPT for context-aware translation"""
        try:
            # Get language names for better prompting
            source_lang_name = self._get_language_name(source_language)
            target_lang_name = self._get_language_name(target_language)
            
            # Create context-aware prompt
            system_prompt = self._create_translation_prompt(
                source_lang_name, target_lang_name, context
            )
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
            
            # Make API call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _call_openai():
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use GPT-3.5 for cost efficiency
                    messages=messages,
                    max_tokens=len(text.split()) * 2,  # Estimate tokens needed
                    temperature=0.3,  # Low temperature for consistent translation
                    top_p=1.0,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
                return response
            
            response = await loop.run_in_executor(None, _call_openai)
            
            translated_text = response.choices[0].message.content.strip()
            
            # Calculate confidence based on response quality
            confidence = self._calculate_openai_confidence(response)
            
            return {
                'translated_text': translated_text,
                'source_language': source_language,
                'target_language': target_language,
                'provider': 'openai',
                'confidence': confidence,
                'error': None,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None
            }
            
        except Exception as e:
            logger.error(f"OpenAI translation error: {str(e)}")
            raise
    
    async def _translate_with_google(
        self, 
        text: str, 
        source_language: str, 
        target_language: str
    ) -> Dict[str, Any]:
        """Translate text using Google Translate API"""
        try:
            # Make API call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _call_google():
                result = self.google_client.translate(
                    text,
                    source_language=source_language,
                    target_language=target_language
                )
                return result
            
            result = await loop.run_in_executor(None, _call_google)
            
            translated_text = result['translatedText']
            detected_source = result.get('detectedSourceLanguage', source_language)
            
            # Google Translate doesn't provide confidence scores, so we estimate
            confidence = 0.85  # Default confidence for Google Translate
            
            return {
                'translated_text': translated_text,
                'source_language': detected_source,
                'target_language': target_language,
                'provider': 'google',
                'confidence': confidence,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Google Translate error: {str(e)}")
            raise
    
    def _create_translation_prompt(
        self, 
        source_lang: str, 
        target_lang: str, 
        context: Optional[str] = None
    ) -> str:
        """Create context-aware translation prompt for OpenAI"""
        base_prompt = f"""You are a professional translator specializing in accurate, context-aware translation from {source_lang} to {target_lang}.

Instructions:
1. Translate the text naturally while preserving the original meaning
2. Maintain the tone and style of the original text
3. Keep technical terms, proper nouns, and specialized vocabulary accurate
4. Preserve formatting and structure
5. If the text contains transcription artifacts (like "um", "uh", repeated words), clean them up naturally
6. Return only the translated text, no explanations or additional comments"""
        
        if context:
            base_prompt += f"\n7. Context: This text is from {context}. Adjust terminology and style accordingly."
        
        return base_prompt
    
    def _get_language_name(self, language_code: str) -> str:
        """Get full language name from language code"""
        language_names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
            'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi',
            'ur': 'Urdu', 'tr': 'Turkish', 'pl': 'Polish', 'nl': 'Dutch',
            'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish',
            'he': 'Hebrew', 'th': 'Thai', 'vi': 'Vietnamese', 'id': 'Indonesian',
            'ms': 'Malay', 'tl': 'Tagalog', 'sw': 'Swahili', 'fa': 'Persian',
            'bn': 'Bengali', 'ta': 'Tamil', 'te': 'Telugu', 'ml': 'Malayalam',
            'kn': 'Kannada', 'gu': 'Gujarati', 'pa': 'Punjabi', 'mr': 'Marathi',
            'ne': 'Nepali', 'si': 'Sinhala', 'my': 'Myanmar', 'km': 'Khmer',
            'lo': 'Lao', 'ka': 'Georgian', 'am': 'Amharic', 'is': 'Icelandic',
            'mt': 'Maltese', 'cy': 'Welsh', 'eu': 'Basque', 'ca': 'Catalan',
            'gl': 'Galician', 'br': 'Breton', 'co': 'Corsican', 'eo': 'Esperanto'
        }
        return language_names.get(language_code, language_code.upper())
    
    def _calculate_openai_confidence(self, response) -> float:
        """Calculate confidence score for OpenAI translation"""
        try:
            # Base confidence
            confidence = 0.9
            
            # Adjust based on finish reason
            if hasattr(response.choices[0], 'finish_reason'):
                if response.choices[0].finish_reason == 'stop':
                    confidence = 0.95
                elif response.choices[0].finish_reason == 'length':
                    confidence = 0.8  # Might be truncated
                else:
                    confidence = 0.7
            
            return confidence
            
        except Exception:
            return 0.85  # Default confidence
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of given text"""
        if not text or not text.strip():
            return {'language': 'unknown', 'confidence': 0.0}
        
        try:
            if self.google_client:
                loop = asyncio.get_event_loop()
                
                def _detect():
                    result = self.google_client.detect_language(text)
                    return result
                
                result = await loop.run_in_executor(None, _detect)
                
                return {
                    'language': result['language'],
                    'confidence': result['confidence']
                }
            else:
                # Fallback: simple heuristic detection (very basic)
                return await self._simple_language_detection(text)
                
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            return {'language': 'unknown', 'confidence': 0.0}
    
    async def _simple_language_detection(self, text: str) -> Dict[str, Any]:
        """Simple heuristic language detection as fallback"""
        # Very basic detection based on character patterns
        # This is a fallback when no proper detection service is available
        
        # Check for common patterns
        if any(ord(char) > 0x4e00 and ord(char) < 0x9fff for char in text):
            return {'language': 'zh', 'confidence': 0.7}  # Chinese characters
        elif any(ord(char) > 0x0600 and ord(char) < 0x06ff for char in text):
            return {'language': 'ar', 'confidence': 0.7}  # Arabic characters
        elif any(ord(char) > 0x3040 and ord(char) < 0x309f for char in text):
            return {'language': 'ja', 'confidence': 0.7}  # Hiragana
        elif any(ord(char) > 0xac00 and ord(char) < 0xd7af for char in text):
            return {'language': 'ko', 'confidence': 0.7}  # Korean
        elif any(ord(char) > 0x0900 and ord(char) < 0x097f for char in text):
            return {'language': 'hi', 'confidence': 0.6}  # Devanagari (Hindi)
        else:
            return {'language': 'en', 'confidence': 0.5}  # Default to English
    
    async def get_supported_languages(self) -> List[Dict[str, Any]]:
        """Get list of supported languages for translation"""
        # Common languages supported by both OpenAI and Google Translate
        supported_languages = [
            {"code": "en", "name": "English", "native": "English"},
            {"code": "es", "name": "Spanish", "native": "Español"},
            {"code": "fr", "name": "French", "native": "Français"},
            {"code": "de", "name": "German", "native": "Deutsch"},
            {"code": "it", "name": "Italian", "native": "Italiano"},
            {"code": "pt", "name": "Portuguese", "native": "Português"},
            {"code": "ru", "name": "Russian", "native": "Русский"},
            {"code": "ja", "name": "Japanese", "native": "日本語"},
            {"code": "ko", "name": "Korean", "native": "한국어"},
            {"code": "zh", "name": "Chinese", "native": "中文"},
            {"code": "ar", "name": "Arabic", "native": "العربية"},
            {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
            {"code": "ur", "name": "Urdu", "native": "اردو"},
            {"code": "tr", "name": "Turkish", "native": "Türkçe"},
            {"code": "pl", "name": "Polish", "native": "Polski"},
            {"code": "nl", "name": "Dutch", "native": "Nederlands"},
            {"code": "sv", "name": "Swedish", "native": "Svenska"},
            {"code": "da", "name": "Danish", "native": "Dansk"},
            {"code": "no", "name": "Norwegian", "native": "Norsk"},
            {"code": "fi", "name": "Finnish", "native": "Suomi"},
            {"code": "he", "name": "Hebrew", "native": "עברית"},
            {"code": "th", "name": "Thai", "native": "ไทย"},
            {"code": "vi", "name": "Vietnamese", "native": "Tiếng Việt"},
            {"code": "id", "name": "Indonesian", "native": "Bahasa Indonesia"},
            {"code": "ms", "name": "Malay", "native": "Bahasa Melayu"},
            {"code": "tl", "name": "Tagalog", "native": "Tagalog"},
            {"code": "sw", "name": "Swahili", "native": "Kiswahili"},
            {"code": "fa", "name": "Persian", "native": "فارسی"},
            {"code": "bn", "name": "Bengali", "native": "বাংলা"},
            {"code": "ta", "name": "Tamil", "native": "தமிழ்"},
            {"code": "te", "name": "Telugu", "native": "తెలుగు"},
            {"code": "ml", "name": "Malayalam", "native": "മലയാളം"},
            {"code": "kn", "name": "Kannada", "native": "ಕನ್ನಡ"},
            {"code": "gu", "name": "Gujarati", "native": "ગુજરાતી"},
            {"code": "pa", "name": "Punjabi", "native": "ਪੰਜਾਬੀ"},
            {"code": "mr", "name": "Marathi", "native": "मराठी"},
            {"code": "ne", "name": "Nepali", "native": "नेपाली"},
            {"code": "si", "name": "Sinhala", "native": "සිංහල"},
            {"code": "my", "name": "Myanmar", "native": "မြန်မာ"},
            {"code": "km", "name": "Khmer", "native": "ខ្មែរ"},
            {"code": "lo", "name": "Lao", "native": "ລາວ"},
            {"code": "ka", "name": "Georgian", "native": "ქართული"},
            {"code": "am", "name": "Amharic", "native": "አማርኛ"},
            {"code": "is", "name": "Icelandic", "native": "Íslenska"},
            {"code": "mt", "name": "Maltese", "native": "Malti"},
            {"code": "cy", "name": "Welsh", "native": "Cymraeg"},
            {"code": "eu", "name": "Basque", "native": "Euskera"},
            {"code": "ca", "name": "Catalan", "native": "Català"},
            {"code": "gl", "name": "Galician", "native": "Galego"},
        ]
        
        return supported_languages

# Global translation service instance
translation_service = TranslationService()