import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ROLE_HOME = { admin: '/admin', worker: '/worker', citizen: '/citizen' }

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@smartwaste.gov.in')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(email, password)
      navigate(ROLE_HOME[user.role] || '/')
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 px-4">
      <div className="card w-full max-w-md">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">Smart Waste System</h1>
        <p className="text-slate-500 text-sm mb-6">Sign in to your account</p>

        {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg mb-4">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-600">Email</label>
            <input className="input mt-1" type="email" value={email}
                   onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Password</label>
            <input className="input mt-1" type="password" value={password}
                   onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary w-full" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-sm text-slate-500 mt-4">
          No account? <Link to="/register" className="text-brand-700 font-medium">Register</Link>
        </p>

        <div className="mt-6 bg-slate-50 rounded-lg p-3 text-xs text-slate-500 space-y-1">
          <p className="font-semibold text-slate-600">Demo credentials (after running seed_data.py):</p>
          <p>Admin: admin@smartwaste.gov.in / admin123</p>
          <p>Worker: worker1@smartwaste.gov.in / worker123</p>
          <p>Citizen: citizen1@example.com / citizen123</p>
        </div>
      </div>
    </div>
  )
}
