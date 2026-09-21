import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ROLE_HOME = { admin: '/admin', worker: '/worker', citizen: '/citizen' }

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', phone: '', role: 'citizen' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await register(form)
      navigate(ROLE_HOME[user.role] || '/')
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 px-4">
      <div className="card w-full max-w-md">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">Create Account</h1>
        <p className="text-slate-500 text-sm mb-6">Register as a citizen to report waste issues, or an admin/worker.</p>

        {error && <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg mb-4">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-600">Full Name</label>
            <input className="input mt-1" name="name" value={form.name} onChange={handleChange} required />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Email</label>
            <input className="input mt-1" type="email" name="email" value={form.email} onChange={handleChange} required />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Phone</label>
            <input className="input mt-1" name="phone" value={form.phone} onChange={handleChange} />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Password</label>
            <input className="input mt-1" type="password" name="password" value={form.password} onChange={handleChange} required minLength={6} />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Role</label>
            <select className="input mt-1" name="role" value={form.role} onChange={handleChange}>
              <option value="citizen">Citizen</option>
              <option value="worker">Worker</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button className="btn btn-primary w-full" disabled={loading}>
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <p className="text-sm text-slate-500 mt-4">
          Already have an account? <Link to="/login" className="text-brand-700 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
