import React from 'react';

const AdminPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Admin Dashboard</h1>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Total Users</h3>
            <p className="text-3xl font-bold text-blue-600">1,234</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Transcriptions</h3>
            <p className="text-3xl font-bold text-green-600">5,678</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Revenue</h3>
            <p className="text-3xl font-bold text-purple-600">$12,345</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">System Health</h3>
            <p className="text-3xl font-bold text-green-600">99.9%</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold">Admin Features</h2>
          </div>
          <div className="p-6">
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-medium mb-2">User Management</h3>
                <p className="text-gray-600 text-sm mb-4">Manage user accounts, subscriptions, and permissions.</p>
                <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">
                  Manage Users
                </button>
              </div>
              <div>
                <h3 className="font-medium mb-2">System Monitoring</h3>
                <p className="text-gray-600 text-sm mb-4">Monitor system performance and usage metrics.</p>
                <button className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors">
                  View Metrics
                </button>
              </div>
              <div>
                <h3 className="font-medium mb-2">Content Moderation</h3>
                <p className="text-gray-600 text-sm mb-4">Review and moderate transcription content.</p>
                <button className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700 transition-colors">
                  Review Content
                </button>
              </div>
              <div>
                <h3 className="font-medium mb-2">Analytics</h3>
                <p className="text-gray-600 text-sm mb-4">View detailed analytics and reports.</p>
                <button className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 transition-colors">
                  View Analytics
                </button>
              </div>
            </div>
            
            <div className="mt-8 p-4 bg-yellow-50 rounded-lg">
              <h4 className="font-medium text-yellow-900 mb-2">Admin Panel Coming Soon</h4>
              <p className="text-yellow-700 text-sm">
                Full admin functionality will be implemented with user management, analytics, and system monitoring.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPage;