import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { Video, Camera, Activity, Clock } from 'lucide-react';
import VideoUpload from './components/VideoUpload';
import WebcamCapture from './components/WebcamCapture';
import ProtectedRoute from './components/ProtectedRoute';
import UserMenu from './components/UserMenu';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import HistoryPage from './pages/HistoryPage';
import { useAuth } from './context/AuthContext';
import { healthCheck } from './services/api';

function App() {
  const { user, loading: authLoading } = useAuth();
  const [apiStatus, setApiStatus] = useState({ status: 'checking', modelLoaded: false });

  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const health = await healthCheck();
        setApiStatus({
          status: 'online',
          modelLoaded: health.model_loaded,
        });
      } catch (err) {
        setApiStatus({
          status: 'offline',
          modelLoaded: false,
        });
      }
    };

    checkApiHealth();
    const interval = setInterval(checkApiHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-blue-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="bg-primary-500 text-white p-2 rounded-lg">
                  🤟
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">ArSL Translator</h1>
                  <p className="text-sm text-gray-600">Arabic Sign Language Recognition</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {/* API Status */}
                <div className="flex items-center gap-2">
                  <Activity
                    className={`w-5 h-5 ${
                      apiStatus.status === 'online'
                        ? 'text-green-500'
                        : apiStatus.status === 'offline'
                        ? 'text-red-500'
                        : 'text-yellow-500'
                    }`}
                  />
                  <div className="text-sm">
                    <div className="font-medium text-gray-700">
                      API: {apiStatus.status === 'online' ? 'Online' : apiStatus.status === 'offline' ? 'Offline' : 'Checking...'}
                    </div>
                    {apiStatus.status === 'online' && (
                      <div className={`text-xs ${apiStatus.modelLoaded ? 'text-green-600' : 'text-yellow-600'}`}>
                        Model: {apiStatus.modelLoaded ? 'Loaded' : 'Not Loaded'}
                      </div>
                    )}
                  </div>
                </div>
                {/* User Menu */}
                <UserMenu />
              </div>
            </div>

            {/* Warning if model not loaded */}
            {apiStatus.status === 'online' && !apiStatus.modelLoaded && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  ⚠️ Model is not loaded. Please train the model first using:
                  <code className="ml-2 px-2 py-1 bg-yellow-100 rounded">docker compose exec api python scripts/phase3_train_baseline.py</code>
                </p>
              </div>
            )}
          </div>
        </header>

        {/* Navigation */}
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8">
              {user && (
                <>
                  <Link
                    to="/upload"
                    className="flex items-center gap-2 px-3 py-4 text-sm font-medium border-b-2 border-transparent hover:border-primary-500 hover:text-primary-600 transition-colors"
                  >
                    <Video className="w-4 h-4" />
                    Video Upload
                  </Link>
                  <Link
                    to="/webcam"
                    className="flex items-center gap-2 px-3 py-4 text-sm font-medium border-b-2 border-transparent hover:border-primary-500 hover:text-primary-600 transition-colors"
                  >
                    <Camera className="w-4 h-4" />
                    Webcam
                  </Link>
                  <Link
                    to="/history"
                    className="flex items-center gap-2 px-3 py-4 text-sm font-medium border-b-2 border-transparent hover:border-primary-500 hover:text-primary-600 transition-colors"
                  >
                    <Clock className="w-4 h-4" />
                    History
                  </Link>
                </>
              )}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={
              <ProtectedRoute><Navigate to="/upload" replace /></ProtectedRoute>
            } />
            <Route path="/upload" element={
              <ProtectedRoute><VideoUpload /></ProtectedRoute>
            } />
            <Route path="/webcam" element={
              <ProtectedRoute><WebcamCapture /></ProtectedRoute>
            } />
            <Route path="/login" element={
              authLoading ? (
                <div className="flex justify-center py-20">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                </div>
              ) : user ? (
                <Navigate to="/upload" replace />
              ) : (
                <LoginPage />
              )
            } />
            <Route path="/register" element={
              authLoading ? (
                <div className="flex justify-center py-20">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                </div>
              ) : user ? (
                <Navigate to="/upload" replace />
              ) : (
                <RegisterPage />
              )
            } />
            <Route path="/profile" element={
              <ProtectedRoute><ProfilePage /></ProtectedRoute>
            } />
            <Route path="/history" element={
              <ProtectedRoute><HistoryPage /></ProtectedRoute>
            } />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-sm text-gray-600">
              Built with ❤️ for Arabic Sign Language Recognition
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
