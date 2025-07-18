#!/usr/bin/env python3
"""
Demo script to show file handler functionality
"""
import asyncio
import os
from app.services.file_handler import file_handler

async def demo_file_operations():
    """Demonstrate file handler operations"""
    print("🚀 File Handler Demo")
    print("=" * 50)
    
    # Create sample audio content (fake MP3 header)
    sample_content = b'\xff\xfb\x90\x00' + b'Sample audio content for demo' + b'\x00' * 500
    filename = "demo_audio.mp3"
    
    try:
        print("1. Validating file...")
        validation_result = await file_handler.validate_file(sample_content, filename)
        print(f"   ✅ File validation successful:")
        print(f"      - Format: {validation_result['format']}")
        print(f"      - Size: {validation_result['file_size']} bytes")
        print(f"      - MIME type: {validation_result['mime_type']}")
        
        print("\n2. Uploading file...")
        upload_result = await file_handler.upload_file(sample_content, filename, "demo_user")
        print(f"   ✅ File upload successful:")
        print(f"      - File ID: {upload_result['file_id']}")
        print(f"      - Storage path: {upload_result['storage_path'] or 'Local storage'}")
        print(f"      - Local path: {upload_result['local_path'] or 'None'}")
        
        # Test file duration detection (will fail without ffprobe, but that's expected)
        if upload_result['local_path']:
            print("\n3. Testing duration detection...")
            duration = await file_handler.get_file_duration(upload_result['local_path'])
            if duration:
                print(f"   ✅ Duration detected: {duration} seconds")
            else:
                print("   ⚠️  Duration detection failed (ffprobe not available)")
        
        print("\n4. Testing file cleanup...")
        await file_handler.delete_file(
            file_path=upload_result['storage_path'],
            local_path=upload_result['local_path']
        )
        print("   ✅ File cleanup completed")
        
        print("\n5. Testing temp file cleanup...")
        await file_handler.cleanup_temp_files(max_age_hours=0)  # Clean all temp files
        print("   ✅ Temp file cleanup completed")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n🎉 Demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_file_operations())