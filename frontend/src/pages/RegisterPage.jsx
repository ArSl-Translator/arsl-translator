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
    <div className="w-full max-w-md">
      <div className="mb-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-gray-950 text-white">
          <Sparkles className="h-5 w-5" />
        </div>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-gray-950">ArSL Studio</h1>
        <p className="mt-2 text-sm text-gray-500">Create your sign-recognition workspace</p>
      </div>

      <div className="panel overflow-hidden">
        <div className="border-b border-gray-200 bg-white px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 text-gray-700">
              <UserPlus className="h-5 w-5" />
            </div>
            <div>
              <p className="section-title">New account</p>
              <h2 className="mt-1 text-xl font-bold tracking-tight text-gray-950">Create account</h2>
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
            <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
            <Field label="Username" value={username} onChange={setUsername} placeholder="Choose a username" minLength={3} />
            <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" minLength={8} />
            <Field label="Confirm password" type="password" value={confirmPassword} onChange={setConfirmPassword} placeholder="Repeat your password" />

            <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <div className="mt-5 rounded-lg border border-gray-200 bg-gray-50 p-3">
            <div className="flex items-center gap-2 text-xs font-bold uppercase text-gray-500">
              <Database className="h-4 w-4 text-blue-600" />
              Persistent history
            </div>
            <p className="mt-2 text-xs leading-5 text-gray-500">
              Your account stores prediction history and dashboard analytics for the demo.
            </p>
          </div>

          <p className="mt-5 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-gray-950 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
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
