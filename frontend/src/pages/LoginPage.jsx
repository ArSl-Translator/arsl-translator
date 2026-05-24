import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogIn, ShieldCheck, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/upload';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md">
      <div className="mb-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-gray-950 text-white">
          <Sparkles className="h-5 w-5" />
        </div>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-gray-950">ArSL Studio</h1>
        <p className="mt-2 text-sm text-gray-500">Arabic sign recognition workspace</p>
      </div>

      <div className="panel overflow-hidden">
        <div className="border-b border-gray-200 bg-white px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 text-gray-700">
              <LogIn className="h-5 w-5" />
            </div>
            <div>
              <p className="section-title">Welcome back!</p>
              <h2 className="mt-1 text-xl font-bold tracking-tight text-gray-950">Sign in</h2>
            </div>
          </div>
        </div>

        <div className="p-6">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-gray-600">Email</label>
              <input type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@example.com" />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-gray-600">Password</label>
              <input type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="Your password" />
            </div>

            <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-5 rounded-lg border border-gray-200 bg-gray-50 p-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase text-gray-500">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Secured project access
            </div>
            <p className="mt-2 text-xs leading-5 text-gray-500">
              Sign in to use prediction history, analytics, video upload, webcam recognition, and the offline chat page.
            </p>
          </div>

          <p className="mt-5 text-center text-sm text-gray-500">
            Do not have an account?{' '}
            <Link to="/register" className="font-semibold text-gray-950 hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
