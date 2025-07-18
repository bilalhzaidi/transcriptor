# 🎵 Audio & Video Transcription App

A powerful full-stack web application for transcribing audio and video files with intelligent YouTube processing, multi-language support, and context-aware translation.

## ✨ Features

- 🎵 **Audio & Video Upload**: Support for multiple formats (MP3, WAV, MP4, AVI, MOV, MKV, etc.)
- 🎬 **YouTube Integration**: Direct transcription from YouTube URLs with intelligent subtitle extraction
- 🌍 **Multi-Language Support**: Transcription and translation to 99+ world languages
- 🧠 **Smart Translation**: Context-aware translation preserving technical terminology
- ⚡ **Real-time Progress**: Live progress tracking with Server-Sent Events
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices
- 🔒 **Secure**: Firebase Authentication with optional user management
- ☁️ **Scalable**: Supabase Storage integration with local fallback

## 🚀 Tech Stack

### Frontend
- **React 18+** with TypeScript
- **Tailwind CSS** for styling
- **Firebase Authentication** for user management
- **Axios** for API communication
- **React Router** for navigation

### Backend
- **FastAPI** with Python 3.8+
- **OpenAI Whisper** for high-quality transcription
- **OpenAI GPT-4** for context-aware translation
- **yt-dlp** for YouTube video processing
- **Supabase** for storage and database
- **Firebase Admin SDK** for authentication

## 🏃‍♂️ Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/bilalhzaidi/transcriptor.git
cd transcriptor
```

2. Start with Docker Compose:
```bash
docker-compose up -d
```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the FastAPI server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

#### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the React development server:
```bash
npm start
```

The application will be available at `http://localhost:3000`

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```bash
# Required
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
TEMP_DIR=temp
MAX_FILE_SIZE=524288000

# Optional (for enhanced features)
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FIREBASE_CREDENTIALS=path_to_firebase_credentials.json
```

#### Frontend (.env)
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_FIREBASE_CONFIG=your_firebase_config
```

## 📚 API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

### Key Endpoints

- `POST /api/transcription/upload` - Upload audio/video files
- `POST /api/transcription/youtube` - Process YouTube videos
- `GET /api/transcription/progress/{task_id}` - Track progress
- `GET /api/transcription/transcript/{task_id}` - Get transcript
- `GET /api/transcription/languages/supported` - Get supported languages

## 🎯 Features in Detail

### YouTube Processing
- **Intelligent Subtitle Extraction**: Automatically detects and uses available subtitles
- **Multi-Language Support**: Supports manual and automatic captions in multiple languages
- **Audio Fallback**: Falls back to audio transcription when subtitles are unavailable
- **Error Handling**: Graceful handling of private/restricted videos

### Translation
- **Context-Aware**: Preserves technical terminology and domain-specific language
- **Multiple Providers**: OpenAI GPT-4 primary, Google Translate fallback
- **Segment-Level**: Translates individual segments for better quality
- **99+ Languages**: Support for major world languages

### File Processing
- **Multiple Formats**: Supports all major audio and video formats
- **Secure Upload**: File validation and size limits
- **Progress Tracking**: Real-time progress updates
- **Automatic Cleanup**: Temporary file management

## 🧪 Testing

Run the test suite:

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**: Configure production environment variables
2. **Database**: Set up Supabase or PostgreSQL database
3. **Storage**: Configure Supabase Storage or AWS S3
4. **Authentication**: Set up Firebase Authentication
5. **SSL**: Configure SSL certificates for HTTPS
6. **Monitoring**: Set up logging and monitoring

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Scale services
docker-compose up -d --scale backend=3

# View logs
docker-compose logs -f
```

## 📊 System Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 2GB
- **Python**: 3.8+
- **Node.js**: 16+

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 10GB+
- **GPU**: CUDA-compatible (for faster processing)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube processing
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [React](https://reactjs.org/) for the frontend framework

## 📞 Support

If you have any questions or need help, please:
1. Check the [API Documentation](http://localhost:8000/docs)
2. Review the [Issues](https://github.com/bilalhzaidi/transcriptor/issues)
3. Create a new issue if needed

---

**Made with ❤️ for the open source community**