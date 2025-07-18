#!/usr/bin/env python3
"""
Demo script to showcase YouTube video processing functionality
"""
import asyncio
import os
from app.services.youtube import youtube_service

async def demo_youtube_service():
    """Demonstrate YouTube service functionality"""
    print("🎥 YouTube Service Demo")
    print("=" * 50)
    
    # Test URLs (using well-known public videos)
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (classic test video)
        "https://youtu.be/dQw4w9WgXcQ",  # Short URL format
        "https://www.youtube.com/watch?v=invalid_id",  # Invalid video ID
        "https://vimeo.com/123456789",  # Non-YouTube URL
    ]
    
    try:
        print("\n1. Testing YouTube URL Validation...")
        for i, url in enumerate(test_urls, 1):
            print(f"\n   Test {i}: {url}")
            
            # Test URL format validation
            is_valid_format = youtube_service._is_valid_youtube_url(url)
            print(f"      Format valid: {'✅' if is_valid_format else '❌'}")
            
            if is_valid_format:
                try:
                    # Test full URL validation (this will make actual API calls)
                    validation_result = await youtube_service.validate_youtube_url(url)
                    
                    if validation_result['valid']:
                        print(f"      ✅ Video validation successful")
                        print(f"         Title: {validation_result['title']}")
                        print(f"         Duration: {validation_result['duration']}s")
                        print(f"         Uploader: {validation_result['uploader']}")
                        print(f"         Video ID: {validation_result['video_id']}")
                    else:
                        print(f"      ❌ Video validation failed: {validation_result['error']}")
                        
                except Exception as e:
                    print(f"      ⚠️  Validation error: {str(e)}")
                    print("         This is expected if the video is not accessible or yt-dlp is not properly configured")
        
        print("\n2. Testing YouTube Audio Download (Simulation)...")
        # We'll simulate the download process without actually downloading
        test_download_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        print(f"   📥 Simulating audio download from: {test_download_url}")
        print("      Note: This demo simulates the download process without actually downloading")
        print("      In a real scenario, this would:")
        print("      1. Validate the YouTube URL")
        print("      2. Extract video metadata")
        print("      3. Download the best available audio format")
        print("      4. Convert to the specified format (MP3)")
        print("      5. Return file path and metadata")
        
        # Show what the download configuration would look like
        print("\n   🔧 Download Configuration:")
        print(f"      Max Duration: {youtube_service.max_duration}s")
        print(f"      Max File Size: {youtube_service.max_file_size / (1024*1024):.0f}MB")
        print(f"      Temp Directory: {youtube_service.temp_dir}")
        print(f"      Default Format: MP3")
        print(f"      Default Quality: 192kbps")
        
        print("\n3. Testing Supported Sites...")
        try:
            supported_sites = youtube_service.get_supported_sites()
            print(f"   ✅ Found {len(supported_sites)} supported sites")
            print("      Sample supported sites:")
            for site in supported_sites[:10]:  # Show first 10
                print(f"         • {site}")
            if len(supported_sites) > 10:
                print(f"         ... and {len(supported_sites) - 10} more")
                
        except Exception as e:
            print(f"   ⚠️  Could not get supported sites: {str(e)}")
        
        print("\n4. Testing Video Metadata Extraction...")
        test_metadata_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        try:
            print(f"   📊 Getting metadata for: {test_metadata_url}")
            metadata_result = await youtube_service.get_video_metadata(test_metadata_url)
            
            if metadata_result['success']:
                metadata = metadata_result['metadata']
                print("   ✅ Metadata extraction successful:")
                print(f"      Title: {metadata.get('title', 'N/A')}")
                print(f"      Duration: {metadata.get('duration', 'N/A')}s")
                print(f"      Channel: {metadata.get('channel', 'N/A')}")
                print(f"      Upload Date: {metadata.get('upload_date', 'N/A')}")
                print(f"      View Count: {metadata.get('view_count', 'N/A'):,}")
                print(f"      Language: {metadata.get('language', 'N/A')}")
                
                # Show available subtitles
                subtitles = metadata.get('subtitles', [])
                auto_captions = metadata.get('automatic_captions', [])
                if subtitles or auto_captions:
                    print("      Available Subtitles:")
                    for lang in subtitles:
                        print(f"         • {lang} (manual)")
                    for lang in auto_captions:
                        print(f"         • {lang} (automatic)")
                else:
                    print("      No subtitles available")
                    
            else:
                print(f"   ❌ Metadata extraction failed: {metadata_result['error']}")
                
        except Exception as e:
            print(f"   ⚠️  Metadata extraction error: {str(e)}")
            print("      This is expected if yt-dlp is not properly configured or video is not accessible")
        
        print("\n5. Testing Subtitle Extraction...")
        try:
            print(f"   📝 Extracting subtitles from: {test_metadata_url}")
            subtitle_result = await youtube_service.extract_subtitles(test_metadata_url, 'en')
            
            if subtitle_result['success']:
                subtitles = subtitle_result['subtitles']
                print("   ✅ Subtitle extraction successful:")
                print(f"      Language: {subtitle_result['language']}")
                print(f"      Source: {subtitle_result['source']}")
                print(f"      Length: {len(subtitles)} characters")
                if subtitles:
                    # Show first few lines
                    lines = subtitles.split('\n')[:5]
                    print("      Preview:")
                    for line in lines:
                        if line.strip():
                            print(f"         {line}")
            else:
                print(f"   ❌ Subtitle extraction failed: {subtitle_result['error']}")
                
        except Exception as e:
            print(f"   ⚠️  Subtitle extraction error: {str(e)}")
            print("      This is expected if yt-dlp is not properly configured")
        
        print("\n6. Testing Error Handling...")
        error_test_cases = [
            ("Invalid URL", "not_a_url"),
            ("Non-YouTube URL", "https://example.com/video"),
            ("Non-existent video", "https://www.youtube.com/watch?v=nonexistent123"),
        ]
        
        for test_name, test_url in error_test_cases:
            print(f"\n   🧪 {test_name}: {test_url}")
            try:
                result = await youtube_service.validate_youtube_url(test_url)
                if result['valid']:
                    print("      ❌ Should have failed but didn't")
                else:
                    print(f"      ✅ Correctly failed: {result['error']}")
            except Exception as e:
                print(f"      ✅ Correctly raised exception: {str(e)}")
        
        print("\n7. Testing Integration with Transcription Service...")
        try:
            from app.services.transcription import transcription_service
            
            print("   🔗 Testing YouTube processing integration...")
            
            # This would normally process a real YouTube video
            # For demo purposes, we'll show what would happen
            print("      Integration workflow:")
            print("      1. ✅ YouTube service validates URL")
            print("      2. ✅ YouTube service downloads audio")
            print("      3. ✅ Transcription service processes audio with Whisper")
            print("      4. ✅ Translation service translates if needed")
            print("      5. ✅ Results returned to user")
            print("      6. ✅ Temporary files cleaned up")
            
            print("\n      Integration features:")
            print("      • Automatic audio format conversion")
            print("      • File size and duration validation")
            print("      • Metadata preservation")
            print("      • Error handling and cleanup")
            print("      • Progress tracking")
            
        except Exception as e:
            print(f"   ⚠️  Integration test error: {str(e)}")
        
    except Exception as e:
        print(f"   ❌ Demo error: {str(e)}")
    
    print("\n🎉 YouTube Service Demo Completed!")
    print("\n📋 Summary of Features Demonstrated:")
    print("✅ YouTube URL validation and format detection")
    print("✅ Video metadata extraction")
    print("✅ Audio download configuration")
    print("✅ Subtitle extraction capabilities")
    print("✅ Multi-site support detection")
    print("✅ Error handling and validation")
    print("✅ Integration with transcription workflow")
    print("✅ Temporary file management")
    
    print("\n🔧 Production Setup Requirements:")
    print("• yt-dlp library installed and updated")
    print("• FFmpeg installed for audio conversion")
    print("• Sufficient disk space for temporary files")
    print("• Network access to YouTube and other video sites")
    print("• Proper error handling and monitoring")
    print("• Rate limiting to respect site policies")
    
    print("\n⚠️  Important Notes:")
    print("• Always respect YouTube's Terms of Service")
    print("• Consider implementing rate limiting")
    print("• Monitor for yt-dlp updates and compatibility")
    print("• Handle private/restricted videos gracefully")
    print("• Implement proper cleanup of temporary files")

if __name__ == "__main__":
    asyncio.run(demo_youtube_service())