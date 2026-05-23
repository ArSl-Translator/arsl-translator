import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Database, Sparkles, UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      await register(email, username, password);
      navigate('/upload', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
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
            <h2 className="mt-8 text-3xl font-bold tracking-tight">Create your workspace</h2>
            <p className="mt-3 text-sm leading-6 text-gray-300">
              Track predictions, evaluate confidence, and keep a clean history for your sign-language experiments.
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="flex items-center gap-2 text-sm font-bold">
              <Database className="h-4 w-4 text-blue-300" />
              Persistent project history
            </div>
            <p className="mt-2 text-xs leading-5 text-gray-400">
              Accounts connect the UI to saved predictions and dashboard analytics.
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-950 text-white">
            <UserPlus className="h-5 w-5" />
          </div>
          <div>
            <p className="section-title">New account</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-gray-950">Create account</h2>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
          <Field label="Username" value={username} onChange={setUsername} placeholder="Choose a username" minLength={3} />
          <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" minLength={8} />
          <Field label="Confirm password" type="password" value={confirmPassword} onChange={setConfirmPassword} placeholder="Repeat your password" />

          <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-gray-950 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', placeholder, minLength }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-semibold text-gray-600">{label}</label>
      <input
        type={type}
        className="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        minLength={minLength}
        placeholder={placeholder}
      />
    </div>
  );
}
