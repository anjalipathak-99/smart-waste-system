import React, { useEffect, useState } from 'react'
import api from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function CitizenPortal() {
  const [bins, setBins] = useState([])
  const [reports, setReports] = useState([])
  const [form, setForm] = useState({ report_type: 'overflow', description: '', bin_id: '' })
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [coords, setCoords] = useState(null)

  const load = async () => {
    const [b, r] = await Promise.all([api.get('/bins'), api.get('/reports')])
    setBins(b.data)
    setReports(r.data)
  }

  useEffect(() => {
    load()
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => {}
      )
    }
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    try {
      const fd = new FormData()
      fd.append('report_type', form.report_type)
      fd.append('description', form.description)
      if (form.bin_id) fd.append('bin_id', form.bin_id)
      if (coords) { fd.append('latitude', coords.lat); fd.append('longitude', coords.lng) }
      if (file) fd.append('image', file)

      await api.post('/reports', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setMessage('Report submitted successfully. Thank you!')
      setForm({ report_type: 'overflow', description: '', bin_id: '' })
      setFile(null)
      load()
    } catch (err) {
      setMessage(err.response?.data?.error || 'Failed to submit report')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Citizen Portal</h1>

      <div className="card">
        <h3 className="font-semibold text-slate-700 mb-3">Report an Issue</h3>
        {message && <div className="bg-blue-50 text-blue-800 text-sm px-3 py-2 rounded-lg mb-3">{message}</div>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-slate-600">Issue Type</label>
              <select className="input mt-1" value={form.report_type}
                      onChange={e => setForm({ ...form, report_type: e.target.value })}>
                <option value="overflow">Overflowing Bin</option>
                <option value="damaged">Damaged Bin</option>
                <option value="missed_collection">Missed Collection</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600">Nearest Bin (optional)</label>
              <select className="input mt-1" value={form.bin_id}
                      onChange={e => setForm({ ...form, bin_id: e.target.value })}>
                <option value="">— Select bin —</option>
                {bins.map(b => <option key={b.id} value={b.id}>{b.code} ({b.area})</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Description</label>
            <textarea className="input mt-1" rows="3" value={form.description}
                      onChange={e => setForm({ ...form, description: e.target.value })}
                      placeholder="Describe what you observed..." />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-600">Photo (optional)</label>
            <input type="file" accept="image/*" className="block text-sm mt-1"
                   onChange={e => setFile(e.target.files[0])} />
          </div>
          {coords && <p className="text-xs text-slate-400">📍 Location will be attached: {coords.lat.toFixed(4)}, {coords.lng.toFixed(4)}</p>}
          <button className="btn btn-primary" disabled={loading}>{loading ? 'Submitting...' : 'Submit Report'}</button>
        </form>
      </div>

      <div className="card">
        <h3 className="font-semibold text-slate-700 mb-3">My Reports</h3>
        {reports.length === 0 && <p className="text-slate-400 text-sm">You haven't submitted any reports yet.</p>}
        <div className="space-y-2">
          {reports.map(r => (
            <div key={r.id} className="flex items-center justify-between border-b last:border-0 py-2">
              <div>
                <div className="text-sm font-medium text-slate-700 capitalize">{r.report_type.replace('_', ' ')}</div>
                <div className="text-xs text-slate-500">{r.description}</div>
                <div className="text-xs text-slate-400">{new Date(r.created_at).toLocaleString()}</div>
              </div>
              <StatusBadge status={r.status} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
