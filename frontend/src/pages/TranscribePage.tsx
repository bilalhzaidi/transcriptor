import React, { useState } from 'react';

const TranscribePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'upload' | 'youtube'>('upload');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Transcribe Audio & Video</h1>
        
        {/* Tab Navigation */}
        <div className="bg-white rounded-lg shadow">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex">
              <button
                onClick={() => setActiveTab('upload')}
                className={`py-4 px-6 text-sm font-medium border-b-2 ${
                  activeTab === 'upload'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Upload Files
              </button>
              <button
                onClick={() => setActiveTab('youtube')}
                className={`py-4 px-6 text-sm font-medium border-b-2 ${
                  activeTab === 'youtube'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                YouTube URL
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'upload' && (
              <div>
                <h3 className="text-lg font-medium mb-4">Upload Audio or Video Files</h3>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                    <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <div className="mt-4">
                    <p className="text-lg text-gray-600">Drop files here or click to browse</p>
                    <p className="text-sm text-gray-500 mt-2">
                      Supports MP3, WAV, MP4, AVI, MOV, MKV and more
                    </p>
                  </div>
                  <button className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Choose Files
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'youtube' && (
              <div>
                <h3 className="text-lg font-medium mb-4">Transcribe YouTube Video</h3>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="youtube-url" className="block text-sm font-medium text-gray-700 mb-2">
                      YouTube URL
                    </label>
                    <input
                      type="url"
                      id="youtube-url"
                      placeholder="https://www.youtube.com/watch?v=..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="target-language" className="block text-sm font-medium text-gray-700 mb-2">
                      Target Language (Optional)
                    </label>
                    <select
                      id="target-language"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Auto-detect</option>
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                      <option value="zh">Chinese</option>
                      <option value="ja">Japanese</option>
                      <option value="ar">Arabic</option>
                      <option value="ur">Urdu</option>
                    </select>
                  </div>
                  
                  <button className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors">
                    Start Transcription
                  </button>
                </div>
              </div>
            )}

            <div className="mt-8 p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Coming Soon</h4>
              <p className="text-blue-700 text-sm">
                Full transcription functionality is being implemented. This will connect to the FastAPI backend 
                for real-time transcription processing.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranscribePage;