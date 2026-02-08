import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink, Navigate } from 'react-router-dom';
import { Video, Camera, Activity, Clock, BarChart3 } from 'lucide-react';
import VideoUpload from './components/VideoUpload';
import WebcamCapture from './components/WebcamCapture';
import ProtectedRoute from './components/ProtectedRoute';
import UserMenu from './components/UserMenu';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import HistoryPage from './pages/HistoryPage';
import DashboardPage from './pages/DashboardPage';
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
      <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-primary-50/30">
        {/* Header */}
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white text-lg shadow-sm">
                  🤟
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900 tracking-tight">ArSL Translator</h1>
                  <p className="text-xs text-gray-500">Arabic Sign Language Recognition</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-gray-50">
                  <Activity
                    className={`w-4 h-4 ${
                      apiStatus.status === 'online'
                        ? 'text-emerald-500'
                        : apiStatus.status === 'offline'
                        ? 'text-red-500'
                        : 'text-amber-500'
                    }`}
                  />
                  <div className="text-xs">
                    <span className="font-medium text-gray-700">
                      {apiStatus.status === 'online' ? 'Online' : apiStatus.status === 'offline' ? 'Offline' : 'Checking...'}
                    </span>
                    {apiStatus.status === 'online' && (
                      <span className={apiStatus.modelLoaded ? 'text-emerald-600' : 'text-amber-600'}>
                        {' '}· {apiStatus.modelLoaded ? 'Model ready' : 'No model'}
                      </span>
                    )}
                  </div>
                </div>
                <UserMenu />
              </div>
            </div>

            {apiStatus.status === 'online' && !apiStatus.modelLoaded && (
              <div className="mt-3 px-4 py-2.5 rounded-xl bg-amber-50 text-amber-800 text-sm">
                ⚠️ Train the model first: <code className="ml-1 px-1.5 py-0.5 bg-amber-100 rounded">docker compose exec api python scripts/phase3_train_baseline.py</code>
              </div>
            )}
          </div>
        </header>

        {/* Navigation */}
        <nav className="bg-white/60 backdrop-blur-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex gap-1 py-2">
              {user && (
                <>
                  <NavLink
                    to="/upload"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                  >
                    <Video className="w-4 h-4" />
                    Video Upload
                  </NavLink>
                  <NavLink
                    to="/webcam"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                  >
                    <Camera className="w-4 h-4" />
                    Webcam
                  </NavLink>
                  <NavLink
                    to="/history"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                  >
                    <Clock className="w-4 h-4" />
                    History
                  </NavLink>
                  <NavLink
                    to="/dashboard"
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                  >
                    <BarChart3 className="w-4 h-4" />
                    Dashboard
                  </NavLink>
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
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-200 border-t-primary-500"></div>
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
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-200 border-t-primary-500"></div>
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
            <Route path="/dashboard" element={
              <ProtectedRoute><DashboardPage /></ProtectedRoute>
            } />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="mt-auto border-t border-gray-100 bg-white/50 py-5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p className="text-sm text-gray-500">
              Built for Arabic Sign Language Recognition
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
