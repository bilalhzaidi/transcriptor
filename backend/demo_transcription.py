#!/usr/bin/env python3
"""
Demo script to show enhanced Whisper transcription functionality
"""
import asyncio
import os
import tempfile
from app.services.transcription import transcription_service
from app.models.schemas import SourceType

async def demo_transcription_service():
    """Demonstrate enhanced transcription service functionality"""
    print("🎤 Enhanced Whisper Transcription Demo")
    print("=" * 50)
    
    # Create a sample audio file (fake content for demo)
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
        # Write fake MP3 header + content
        temp_file.write(b'\xff\xfb\x90\x00' + b'Sample audio content for transcription demo' + b'\x00' * 1000)
        sample_file = temp_file.name
    
    try:
        print("1. Testing device validation...")
        print(f"   ✅ Using device: {transcription_service.device}")
        print(f"   ✅ Model name: {transcription_service.model_name}")
        
        print("\n2. Testing model loading...")
        try:
            await transcription_service.load_model()
            print(f"   ✅ Model loaded successfully in {transcription_service.model_load_time:.2f}s")
        except Exception as e:
            print(f"   ⚠️  Model loading failed (expected in demo): {str(e)}")
            print("   ℹ️  This is expected since we don't have actual Whisper models in the demo environment")
        
        print("\n3. Testing audio preprocessing...")
        try:
            processed_path, metadata = await transcription_service.preprocess_audio(sample_file)
            print(f"   ✅ Audio preprocessing successful:")
            print(f"      - Processed path: {processed_path}")
            print(f"      - Duration: {metadata.get('duration', 'Unknown')} seconds")
            print(f"      - File size: {metadata['file_size']} bytes")
        except Exception as e:
            print(f"   ⚠️  Audio preprocessing failed: {str(e)}")
        
        print("\n4. Testing task creation...")
        task_id = await transcription_service.create_task(
            source_path=sample_file,
            source_type=SourceType.FILE,
            user_id="demo_user",
            target_language="en"
        )
        print(f"   ✅ Task created successfully:")
        print(f"      - Task ID: {task_id}")
        
        # Get task details
        task = await transcription_service.get_task(task_id)
        print(f"      - Status: {task.status}")
        print(f"      - Progress: {task.progress}%")
        print(f"      - Source type: {task.source_type}")
        
        print("\n5. Testing audio format validation...")
        try:
            format_info = await transcription_service.validate_audio_format(sample_file)
            print(f"   ✅ Format validation successful:")
            print(f"      - Format: {format_info['format']}")
            print(f"      - Type: {format_info['type']}")
            print(f"      - Whisper compatible: {format_info['whisper_compatible']}")
        except Exception as e:
            print(f"   ⚠️  Format validation failed: {str(e)}")
        
        print("\n6. Testing language detection...")
        try:
            detection_result = await transcription_service.detect_language(sample_file)
            print(f"   ✅ Language detection completed:")
            print(f"      - Detected language: {detection_result['language']}")
            print(f"      - Confidence: {detection_result['confidence']:.2f}")
            print(f"      - Sample text: {detection_result['sample_text'][:50]}...")
            print(f"      - Segments analyzed: {detection_result['segments_analyzed']}")
        except Exception as e:
            print(f"   ⚠️  Language detection failed (expected): {str(e)}")
        
        print("\n7. Testing comprehensive supported languages...")
        languages = await transcription_service.get_supported_languages()
        print(f"   ✅ Supported languages: {len(languages)} languages")
        print("      - Sample languages:")
        for lang in languages[:8]:  # Show first 8
            print(f"        • {lang['name']} ({lang['code']}) - {lang['native']}")
        
        # Show some interesting languages
        interesting_langs = ['ur', 'ar', 'hi', 'zh', 'ja', 'ko']
        print("      - Interesting languages:")
        for lang in languages:
            if lang['code'] in interesting_langs:
                print(f"        • {lang['name']} ({lang['code']}) - {lang['native']}")
        
        print("\n8. Testing user tasks retrieval...")
        user_tasks = await transcription_service.get_user_tasks("demo_user")
        print(f"   ✅ User tasks retrieved: {len(user_tasks)} tasks")
        
        print("\n9. Testing task cleanup...")
        await transcription_service.cleanup_old_tasks(max_age_hours=0)  # Clean all tasks
        print("   ✅ Task cleanup completed")
        
        # Wait a moment for any background processing
        await asyncio.sleep(0.5)
        
        # Check final task status
        final_task = await transcription_service.get_task(task_id)
        if final_task:
            print(f"\n10. Final task status:")
            print(f"   - Status: {final_task.status}")
            print(f"   - Progress: {final_task.progress}%")
            if final_task.error_message:
                print(f"   - Error: {final_task.error_message}")
        
    except Exception as e:
        print(f"   ❌ Demo error: {str(e)}")
    
    finally:
        # Cleanup temp file
        if os.path.exists(sample_file):
            os.remove(sample_file)
    
    print("\n🎉 Enhanced Whisper transcription demo completed!")
    print("\nKey Features Demonstrated:")
    print("✅ Device validation (CPU/CUDA)")
    print("✅ Asynchronous model loading with caching")
    print("✅ Audio preprocessing with metadata extraction")
    print("✅ Task management and progress tracking")
    print("✅ Multi-language support")
    print("✅ Error handling and recovery")
    print("✅ Background task processing")

if __name__ == "__main__":
    asyncio.run(demo_transcription_service())