import React from 'react';

const HistoryPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Transcription History</h1>
        
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold">Recent Transcriptions</h2>
          </div>
          
          <div className="p-6">
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900">No transcriptions yet</h3>
              <p className="mt-2 text-gray-600">
                Start by uploading an audio file or pasting a YouTube URL to see your transcription history here.
              </p>
              <div className="mt-6">
                <a 
                  href="/transcribe" 
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Start Transcribing
                </a>
              </div>
            </div>
            
            <div className="mt-8 p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Coming Soon</h4>
              <p className="text-blue-700 text-sm">
                Your transcription history will show completed transcriptions with options to:
              </p>
              <ul className="mt-2 text-blue-700 text-sm space-y-1">
                <li>• View and edit transcripts</li>
                <li>• Download in multiple formats</li>
                <li>• Search through your history</li>
                <li>• Organize with tags and folders</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;