import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { User, LogOut, Clock, LogIn, UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Link
          to="/login"
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-600 hover:text-primary-600 rounded-xl hover:bg-primary-50/80 transition-colors"
        >
          <LogIn className="w-4 h-4" />
          Sign In
        </Link>
        <Link
          to="/register"
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-primary-500 rounded-xl hover:bg-primary-600 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Sign Up
        </Link>
      </div>
    );
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-gray-100 transition-colors"
      >
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-100 to-primary-50 text-primary-600 flex items-center justify-center text-sm font-bold">
          {user.username.charAt(0).toUpperCase()}
        </div>
        <span className="text-sm font-medium text-gray-700 hidden sm:block">{user.username}</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-white/95 backdrop-blur-md rounded-xl py-1.5 z-50 border border-gray-100">
          <Link
            to="/profile"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg mx-1 transition-colors"
          >
            <User className="w-4 h-4" />
            Profile
          </Link>
          <Link
            to="/history"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg mx-1 transition-colors"
          >
            <Clock className="w-4 h-4" />
            History
          </Link>
          <hr className="my-1 border-gray-100" />
          <button
            onClick={() => {
              setOpen(false);
              logout();
            }}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-lg mx-1 transition-colors text-left"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
