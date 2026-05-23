import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink, Navigate } from 'react-router-dom';
import { Activity, BarChart3, Bluetooth, Camera, Clock, ShieldCheck, Sparkles, Video } from 'lucide-react';
import VideoUpload from './components/VideoUpload';
import WebcamCapture from './components/WebcamCapture';
import ProtectedRoute from './components/ProtectedRoute';
import UserMenu from './components/UserMenu';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import HistoryPage from './pages/HistoryPage';
import DashboardPage from './pages/DashboardPage';
import OfflineChatPage from './pages/OfflineChatPage';
import { useAuth } from './context/AuthContext';
import { healthCheck } from './services/api';

const navItems = [
  { to: '/upload', label: 'Video Upload', short: 'Upload', icon: Video },
  { to: '/webcam', label: 'Webcam Capture', short: 'Webcam', icon: Camera },
  { to: '/history', label: 'History', short: 'History', icon: Clock },
  { to: '/dashboard', label: 'Analytics', short: 'Analytics', icon: BarChart3 },
  { to: '/offline-chat', label: 'Offline Chat', short: 'Chat', icon: Bluetooth },
];

function StatusPill({ apiStatus }) {
  const online = apiStatus.status === 'online';
  const offline = apiStatus.status === 'offline';

  return (
    <div className="hidden sm:flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
      <Activity
        className={`h-4 w-4 ${
          online ? 'text-emerald-500' : offline ? 'text-red-500' : 'text-amber-500'
        }`}
      />
      <span className="text-xs font-semibold text-gray-700">
        {online
          ? apiStatus.modelLoaded
            ? 'Models ready'
            : 'API online'
          : offline
          ? 'API offline'
          : 'Checking'}
      </span>
    </div>
  );
}

function AppShell({ user, apiStatus, authLoading }) {
  return (
    <div className="min-h-screen bg-[#f7f8fb]">
      <div className="min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
        {user && (
          <aside className="hidden min-h-screen flex-col border-r border-gray-200 bg-[#f1f3f7] px-4 py-5 lg:flex">
            <Link to="/upload" className="flex items-center gap-3 px-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-950 text-white">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-tight text-gray-950">ArSL Studio</h1>
                <p className="text-xs font-medium text-gray-500">Arabic sign intelligence</p>
              </div>
            </Link>

            <nav className="mt-8 space-y-1">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                  <Icon className="h-4 w-4" />
                  {label}
                </NavLink>
              ))}
            </nav>

            <div className="mt-auto rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-center gap-2 text-sm font-bold text-gray-900">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                Local-first assistive layer
              </div>
              <p className="mt-2 text-xs leading-5 text-gray-500">
                Trained landmark models, browser capture, and Bluetooth mobile chat in one platform.
              </p>
            </div>
          </aside>
        )}

        <div className="min-w-0">
          <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur">
            <div className="px-4 py-3 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 lg:hidden">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-950 text-white">
                      <Sparkles className="h-4 w-4" />
                    </div>
                    <div>
                      <h1 className="text-base font-bold text-gray-950">ArSL Studio</h1>
                      <p className="text-xs text-gray-500">Arabic sign intelligence</p>
                    </div>
                  </div>
                  <div className="hidden lg:block">
                    <p className="section-title">Recognition workspace</p>
                    <h2 className="mt-1 text-2xl font-bold tracking-tight text-gray-950">
                      Translate signs from video, webcam, or offline chat.
                    </h2>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <StatusPill apiStatus={apiStatus} />
                  <UserMenu />
                </div>
              </div>

              {user && (
                <nav className="mt-3 flex gap-1 overflow-x-auto pb-1 lg:hidden">
                  {navItems.map(({ to, short, icon: Icon }) => (
                    <NavLink key={to} to={to} className={({ isActive }) => `nav-link shrink-0 ${isActive ? 'active' : ''}`}>
                      <Icon className="h-4 w-4" />
                      {short}
                    </NavLink>
                  ))}
                </nav>
              )}

              {apiStatus.status === 'online' && !apiStatus.modelLoaded && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-800">
                  API is online, but no model checkpoint is loaded.
                </div>
              )}
            </div>
          </header>

          <main className="px-4 py-6 sm:px-6 lg:px-8">
            <Routes>
              <Route path="/" element={<ProtectedRoute><Navigate to="/upload" replace /></ProtectedRoute>} />
              <Route path="/upload" element={<ProtectedRoute><VideoUpload /></ProtectedRoute>} />
              <Route path="/webcam" element={<ProtectedRoute><WebcamCapture /></ProtectedRoute>} />
              <Route
                path="/login"
                element={
                  authLoading ? (
                    <div className="flex justify-center py-20">
                      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
                    </div>
                  ) : user ? (
                    <Navigate to="/upload" replace />
                  ) : (
                    <LoginPage />
                  )
                }
              />
              <Route
                path="/register"
                element={
                  authLoading ? (
                    <div className="flex justify-center py-20">
                      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
                    </div>
                  ) : user ? (
                    <Navigate to="/upload" replace />
                  ) : (
                    <RegisterPage />
                  )
                }
              />
              <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
              <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
              <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
              <Route path="/offline-chat" element={<ProtectedRoute><OfflineChatPage /></ProtectedRoute>} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}

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
    const interval = setInterval(checkApiHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Router>
      <AppShell user={user} apiStatus={apiStatus} authLoading={authLoading} />
    </Router>
  );
}

export default App;
