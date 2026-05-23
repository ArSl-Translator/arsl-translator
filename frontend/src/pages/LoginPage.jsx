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
    <div className="mx-auto grid max-w-5xl overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm lg:grid-cols-[1fr_420px]">
      <div className="hidden bg-gray-950 p-8 text-white lg:block">
        <div className="flex h-full flex-col justify-between">
          <div>
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-white text-gray-950">
              <Sparkles className="h-5 w-5" />
            </div>
            <h2 className="mt-8 text-3xl font-bold tracking-tight">ArSL Studio</h2>
            <p className="mt-3 text-sm leading-6 text-gray-300">
              Secure access to Arabic sign recognition, prediction history, analytics, and the offline chat companion.
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="flex items-center gap-2 text-sm font-bold">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              Assistive AI workspace
            </div>
            <p className="mt-2 text-xs leading-5 text-gray-400">
              Built for video inference, webcam capture, and offline communication demos.
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-950 text-white">
            <LogIn className="h-5 w-5" />
          </div>
          <div>
            <p className="section-title">Welcome back</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-gray-950">Sign in</h2>
          </div>
        </div>

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

        <p className="mt-5 text-center text-sm text-gray-500">
          Do not have an account?{' '}
          <Link to="/register" className="font-semibold text-gray-950 hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
