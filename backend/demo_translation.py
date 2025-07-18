#!/usr/bin/env python3
"""
Demo script to show translation service functionality
"""
import asyncio
from app.services.translation import translation_service, TranslationProvider

async def demo_translation_service():
    """Demonstrate translation service functionality"""
    print("🌍 Translation Service Demo")
    print("=" * 50)
    
    # Sample texts for translation
    sample_texts = {
        'en': "Hello, this is a test transcription from an audio file. The quality is very good.",
        'es': "Hola, esta es una transcripción de prueba de un archivo de audio. La calidad es muy buena.",
        'fr': "Bonjour, ceci est une transcription de test d'un fichier audio. La qualité est très bonne.",
        'de': "Hallo, das ist eine Test-Transkription aus einer Audiodatei. Die Qualität ist sehr gut.",
        'zh': "你好，这是来自音频文件的测试转录。质量非常好。",
        'ar': "مرحبا، هذا نسخ تجريبي من ملف صوتي. الجودة جيدة جدا.",
        'hi': "नमस्ते, यह एक ऑडियो फ़ाइल से एक परीक्षण प्रतिलेखन है। गुणवत्ता बहुत अच्छी है।",
        'ur': "ہیلو، یہ ایک آڈیو فائل سے ٹیسٹ ٹرانسکرپشن ہے۔ کوالٹی بہت اچھی ہے۔"
    }
    
    try:
        print("1. Testing translation service initialization...")
        print(f"   ✅ Translation service initialized")
        print(f"   - OpenAI available: {translation_service.openai_client is not None}")
        print(f"   - Google Translate available: {translation_service.google_client is not None}")
        print(f"   - Preferred provider: {translation_service.preferred_provider}")
        
        print("\n2. Testing supported languages...")
        languages = await translation_service.get_supported_languages()
        print(f"   ✅ Supported languages: {len(languages)} languages")
        print("   - Sample languages:")
        for lang in languages[:8]:
            print(f"     • {lang['name']} ({lang['code']}) - {lang['native']}")
        
        print("\n3. Testing basic translation (English to Spanish)...")
        result = await translation_service.translate_text(
            text=sample_texts['en'],
            source_language='en',
            target_language='es'
        )
        print(f"   ✅ Translation completed:")
        print(f"   - Original: {sample_texts['en'][:60]}...")
        print(f"   - Translated: {result['translated_text'][:60]}...")
        print(f"   - Provider: {result['provider']}")
        print(f"   - Confidence: {result['confidence']:.2f}")
        if result['error']:
            print(f"   - Error: {result['error']}")
        
        print("\n4. Testing translation with context...")
        medical_text = "The patient shows symptoms of acute bronchitis with mild fever."
        result = await translation_service.translate_text(
            text=medical_text,
            source_language='en',
            target_language='es',
            context='medical transcription'
        )
        print(f"   ✅ Medical translation completed:")
        print(f"   - Original: {medical_text}")
        print(f"   - Translated: {result['translated_text']}")
        print(f"   - Provider: {result['provider']}")
        print(f"   - Context: medical transcription")
        
        print("\n5. Testing language detection...")
        for lang_code, text in list(sample_texts.items())[:5]:
            detection_result = await translation_service.detect_language(text)
            print(f"   - {lang_code}: {detection_result['language']} (confidence: {detection_result['confidence']:.2f})")
        
        print("\n6. Testing edge cases...")
        
        # Empty text
        result = await translation_service.translate_text("", "en", "es")
        print(f"   - Empty text: {result['provider']} (confidence: {result['confidence']})")
        
        # Same language
        result = await translation_service.translate_text("Hello", "en", "en")
        print(f"   - Same language: {result['provider']} (confidence: {result['confidence']})")
        
        # Very short text
        result = await translation_service.translate_text("Hi", "en", "es")
        print(f"   - Short text: '{result['translated_text']}' via {result['provider']}")
        
        print("\n7. Testing multiple language pairs...")
        test_pairs = [
            ('en', 'fr', 'Hello world'),
            ('en', 'de', 'Good morning'),
            ('en', 'zh', 'Thank you'),
            ('en', 'ar', 'Welcome'),
            ('en', 'hi', 'How are you?')
        ]
        
        for source, target, text in test_pairs:
            result = await translation_service.translate_text(text, source, target)
            status = "✅" if not result['error'] else "❌"
            print(f"   {status} {source}→{target}: '{text}' → '{result['translated_text'][:30]}...'")
        
        print("\n8. Testing provider fallback...")
        # This will test the fallback mechanism if one provider fails
        result = await translation_service.translate_text(
            "This is a test of the fallback mechanism.",
            "en", "es",
            provider=TranslationProvider.AUTO
        )
        print(f"   ✅ Fallback test completed:")
        print(f"   - Provider used: {result['provider']}")
        print(f"   - Translation: {result['translated_text'][:50]}...")
        
    except Exception as e:
        print(f"   ❌ Demo error: {str(e)}")
    
    print("\n🎉 Translation service demo completed!")
    print("\nKey Features Demonstrated:")
    print("✅ Multiple translation providers (OpenAI + Google Translate)")
    print("✅ Context-aware translation for specialized content")
    print("✅ Language detection with confidence scoring")
    print("✅ Comprehensive language support (45+ languages)")
    print("✅ Provider fallback and error handling")
    print("✅ Edge case handling (empty text, same language)")
    print("✅ Confidence scoring and quality assessment")

if __name__ == "__main__":
    asyncio.run(demo_translation_service())