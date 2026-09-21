import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const roleHome = {
    admin: '/admin',
    worker: '/worker',
    citizen: '/citizen',
  }

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
        <Link to={user ? roleHome[user.role] : '/'} className="flex items-center gap-2 font-bold text-lg text-brand-700">
          <span>🗑️</span> Smart Waste System
        </Link>
        <div className="flex items-center gap-4">
          {user && (
            <>
              <Link to="/classify" className="text-sm text-slate-600 hover:text-brand-700 font-medium">
                📷 Classify Waste
              </Link>
              <span className="text-sm text-slate-500 hidden sm:inline">
                {user.name} <span className="badge bg-brand-100 text-brand-800 ml-1">{user.role}</span>
              </span>
              <button
                className="btn btn-secondary text-sm"
                onClick={() => { logout(); navigate('/login') }}
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
