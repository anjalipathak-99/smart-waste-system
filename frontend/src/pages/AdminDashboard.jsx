import React, { useEffect, useState, useCallback } from 'react'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, ArcElement,
  PointElement, LineElement, Title, Tooltip, Legend,
} from 'chart.js'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import api from '../api/client'
import StatusBadge from '../components/StatusBadge'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, PointElement, LineElement, Title, Tooltip, Legend)

const STATUS_COLORS = { normal: '#22c55e', warning: '#eab308', critical: '#ef4444', damaged: '#6b7280' }

const binIcon = (status) => L.divIcon({
  className: '',
  html: `<div style="background:${STATUS_COLORS[status] || '#64748b'};width:16px;height:16px;border-radius:50%;border:2px solid white;box-shadow:0 0 4px rgba(0,0,0,0.4)"></div>`,
  iconSize: [16, 16],
})

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null)
  const [bins, setBins] = useState([])
  const [alerts, setAlerts] = useState([])
  const [predictions, setPredictions] = useState([])
  const [workers, setWorkers] = useState([])
  const [tab, setTab] = useState('overview')
  const [routeResult, setRouteResult] = useState(null)
  const [selectedWorker, setSelectedWorker] = useState('')
  const [algorithm, setAlgorithm] = useState('A*')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const loadAll = useCallback(async () => {
    const [s, b, a, w] = await Promise.all([
      api.get('/dashboard/summary'),
      api.get('/bins'),
      api.get('/dashboard/alerts'),
      api.get('/workers'),
    ])
    setSummary(s.data)
    setBins(b.data)
    setAlerts(a.data)
    setWorkers(w.data)
  }, [])

  useEffect(() => { loadAll() }, [loadAll])

  const runSimulationTick = async () => {
    setBusy(true)
    setMessage('')
    try {
      const res = await api.post('/bins/simulate/tick', { minutes: 90 })
      setMessage(`Simulation advanced. ${res.data.new_alerts.length} new alert(s) generated.`)
      await loadAll()
    } finally {
      setBusy(false)
    }
  }

  const trainModels = async () => {
    setBusy(true)
    setMessage('')
    try {
      const res = await api.post('/predictions/train')
      setMessage(
        `Overflow model: ${res.data.overflow_model.trained ? 'trained (MAE ' + res.data.overflow_model.mae + '%)' : res.data.overflow_model.reason} | ` +
        `Forecast model: ${res.data.forecast_model.trained ? 'trained (MAE ' + res.data.forecast_model.mae + ' kg)' : res.data.forecast_model.reason}`
      )
    } finally {
      setBusy(false)
    }
  }

  const loadPredictions = async () => {
    const res = await api.get('/predictions/overflow')
    setPredictions(res.data)
    setTab('predictions')
  }

  const optimizeRoute = async () => {
    if (!selectedWorker) { setMessage('Select a worker first'); return }
    setBusy(true)
    setMessage('')
    try {
      const res = await api.post('/routes/optimize', { worker_id: Number(selectedWorker), algorithm })
      setRouteResult(res.data)
      setTab('routes')
    } catch (err) {
      setMessage(err.response?.data?.error || 'Route optimization failed')
    } finally {
      setBusy(false)
    }
  }

  const resolveAlert = async (id) => {
    await api.post(`/dashboard/alerts/${id}/resolve`)
    setAlerts(alerts.map(a => a.id === id ? { ...a, is_resolved: true } : a))
  }

  if (!summary) return <div className="p-8 text-center text-slate-500">Loading dashboard...</div>

  const statusChartData = {
    labels: Object.keys(summary.status_counts),
    datasets: [{
      data: Object.values(summary.status_counts),
      backgroundColor: Object.keys(summary.status_counts).map(s => STATUS_COLORS[s] || '#94a3b8'),
    }],
  }

  const typeChartData = {
    labels: Object.keys(summary.type_counts),
    datasets: [{ label: 'Bins by waste type', data: Object.values(summary.type_counts), backgroundColor: '#16a34a' }],
  }

  const areaFillData = {
    labels: Object.keys(summary.area_avg_fill),
    datasets: [{ label: 'Avg fill level (%)', data: Object.values(summary.area_avg_fill), backgroundColor: '#0ea5e9' }],
  }

  const classificationData = {
    labels: Object.keys(summary.classification_breakdown_7d),
    datasets: [{ label: 'Classifications (7d)', data: Object.values(summary.classification_breakdown_7d), backgroundColor: '#f97316' }],
  }

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-800">Admin Dashboard</h1>
        <div className="flex flex-wrap gap-2">
          <button className="btn btn-secondary text-sm" onClick={runSimulationTick} disabled={busy}>
            ⏱ Advance Simulation
          </button>
          <button className="btn btn-secondary text-sm" onClick={trainModels} disabled={busy}>
            🧠 Train ML Models
          </button>
          <button className="btn btn-primary text-sm" onClick={loadPredictions}>
            📈 Overflow Predictions
          </button>
        </div>
      </div>

      {message && <div className="bg-blue-50 text-blue-800 text-sm px-4 py-2 rounded-lg">{message}</div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Bins" value={summary.total_bins} />
        <StatCard label="Unresolved Alerts" value={summary.unresolved_alerts} accent="text-red-600" />
        <StatCard label="Pending Reports" value={summary.pending_reports} accent="text-yellow-600" />
        <StatCard label="Active Routes" value={summary.active_routes} accent="text-blue-600" />
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {['overview', 'map', 'bins', 'alerts', 'predictions', 'routes'].map(t => (
          <button key={t}
                  className={`px-4 py-2 text-sm font-medium capitalize border-b-2 ${tab === t ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500'}`}
                  onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">Bin Status Distribution</h3>
            <Doughnut data={statusChartData} />
          </div>
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">Bins by Waste Type</h3>
            <Bar data={typeChartData} />
          </div>
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">Average Fill Level by Area</h3>
            <Bar data={areaFillData} />
          </div>
          <div className="card">
            <h3 className="font-semibold text-slate-700 mb-3">AI Classifications (Last 7 Days)</h3>
            {Object.keys(summary.classification_breakdown_7d).length > 0
              ? <Bar data={classificationData} />
              : <p className="text-sm text-slate-400">No classifications yet — try the Classify Waste page.</p>}
          </div>
        </div>
      )}

      {tab === 'map' && (
        <div className="card p-0 overflow-hidden">
          <MapContainer center={[28.67, 77.38]} zoom={12} style={{ height: '520px', width: '100%' }}>
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                       attribution='&copy; OpenStreetMap contributors' />
            {bins.map(b => (
              <Marker key={b.id} position={[b.latitude, b.longitude]} icon={binIcon(b.status)}>
                <Popup>
                  <strong>{b.code}</strong> ({b.bin_type})<br />
                  Area: {b.area}<br />
                  Fill: {b.fill_level}% | Status: {b.status}<br />
                  Weight: {b.weight_kg} kg | Temp: {b.temperature_c}°C
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      )}

      {tab === 'bins' && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2 pr-4">Code</th><th className="pr-4">Area</th><th className="pr-4">Type</th>
                <th className="pr-4">Fill %</th><th className="pr-4">Weight (kg)</th><th className="pr-4">Temp (°C)</th>
                <th className="pr-4">Status</th><th className="pr-4">Last Collected</th>
              </tr>
            </thead>
            <tbody>
              {bins.map(b => (
                <tr key={b.id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="py-2 pr-4 font-medium">{b.code}</td>
                  <td className="pr-4">{b.area}</td>
                  <td className="pr-4">{b.bin_type}</td>
                  <td className="pr-4">{b.fill_level}%</td>
                  <td className="pr-4">{b.weight_kg}</td>
                  <td className="pr-4">{b.temperature_c}</td>
                  <td className="pr-4"><StatusBadge status={b.status} /></td>
                  <td className="pr-4 text-slate-400">{b.last_collected_at ? new Date(b.last_collected_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'alerts' && (
        <div className="card">
          <div className="space-y-2">
            {alerts.length === 0 && <p className="text-slate-400 text-sm">No alerts.</p>}
            {alerts.map(a => (
              <div key={a.id} className="flex items-center justify-between border-b last:border-0 py-2">
                <div>
                  <div className="text-sm font-medium text-slate-700">{a.bin_code}: {a.message}</div>
                  <div className="text-xs text-slate-400">{new Date(a.created_at).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={a.severity} />
                  {a.is_resolved
                    ? <StatusBadge status="resolved" />
                    : <button className="btn btn-secondary text-xs" onClick={() => resolveAlert(a.id)}>Resolve</button>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'predictions' && (
        <div className="card overflow-x-auto">
          <p className="text-sm text-slate-500 mb-3">
            ML-predicted fill levels (RandomForestRegressor, falls back to per-bin linear trend if the model hasn't been trained yet — click "Train ML Models" above first for best results).
          </p>
          {predictions.length === 0
            ? <p className="text-slate-400 text-sm">Click "Overflow Predictions" above to run the model.</p>
            : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b">
                    <th className="py-2 pr-4">Bin</th><th className="pr-4">Area</th><th className="pr-4">Now</th>
                    <th className="pr-4">+6h</th><th className="pr-4">+12h</th><th className="pr-4">+24h</th>
                    <th className="pr-4">Hrs to Overflow</th><th className="pr-4">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map(p => (
                    <tr key={p.bin_id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{p.bin_code}</td>
                      <td className="pr-4">{p.area}</td>
                      <td className="pr-4">{p.current_fill_level}%</td>
                      <td className="pr-4">{p.predictions['+6h']}%</td>
                      <td className="pr-4">{p.predictions['+12h']}%</td>
                      <td className="pr-4">{p.predictions['+24h']}%</td>
                      <td className="pr-4">{p.predicted_hours_to_overflow ?? '—'}</td>
                      <td className="pr-4"><StatusBadge status={p.risk_level === 'critical' || p.risk_level === 'high' ? 'critical' : p.risk_level === 'medium' ? 'warning' : 'normal'} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {tab === 'routes' && (
        <div className="space-y-4">
          <div className="card flex flex-wrap items-end gap-3">
            <div>
              <label className="text-sm font-medium text-slate-600 block mb-1">Worker</label>
              <select className="input" value={selectedWorker} onChange={e => setSelectedWorker(e.target.value)}>
                <option value="">Select worker</option>
                {workers.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600 block mb-1">Algorithm</label>
              <select className="input" value={algorithm} onChange={e => setAlgorithm(e.target.value)}>
                <option value="A*">A*</option>
                <option value="Dijkstra">Dijkstra</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={optimizeRoute} disabled={busy}>
              Generate Optimized Route
            </button>
            <span className="text-xs text-slate-400">Optimizes over all bins currently in "warning" or "critical" status.</span>
          </div>

          {routeResult && (
            <div className="card">
              <h3 className="font-semibold text-slate-700 mb-2">
                Route #{routeResult.id} for {routeResult.worker_name} — {routeResult.algorithm_used}
              </h3>
              <p className="text-sm text-slate-500 mb-3">
                Total distance: <strong>{routeResult.total_distance_km} km</strong> · Estimated time: <strong>{routeResult.estimated_time_min} min</strong>
              </p>
              <ol className="space-y-1 text-sm">
                <li className="text-slate-400">🏭 Start: Municipal Collection Yard</li>
                {routeResult.stops.map((s, idx) => (
                  <li key={s.id}>
                    {idx + 1}. Bin {s.bin.code} ({s.bin.area}) — {s.bin.fill_level}% full
                    {routeResult.legs[idx] && <span className="text-slate-400"> — {routeResult.legs[idx].distance_km} km leg</span>}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, accent }) {
  return (
    <div className="card">
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${accent || 'text-slate-800'}`}>{value}</div>
    </div>
  )
}
