import React, { useEffect, useState } from 'react'
import api from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function WorkerPortal() {
  const [routes, setRoutes] = useState([])
  const [busy, setBusy] = useState(null)

  const load = async () => {
    const res = await api.get('/routes')
    setRoutes(res.data)
  }

  useEffect(() => { load() }, [])

  const completeStop = async (stopId) => {
    setBusy(stopId)
    try {
      await api.post(`/routes/stops/${stopId}/complete`)
      await load()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">My Collection Routes</h1>

      {routes.length === 0 && (
        <div className="card text-slate-400 text-sm">
          No routes assigned yet. An admin needs to generate an optimized route for you from the Admin Dashboard → Routes tab.
        </div>
      )}

      {routes.map(route => (
        <div key={route.id} className="card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-slate-700">Route #{route.id} — {route.route_date}</h3>
              <p className="text-xs text-slate-500">
                {route.total_distance_km} km · ~{route.estimated_time_min} min · {route.algorithm_used}
              </p>
            </div>
            <StatusBadge status={route.status} />
          </div>
          <ol className="space-y-2">
            {route.stops.map((s, idx) => (
              <li key={s.id} className="flex items-center justify-between border-b last:border-0 py-2">
                <div className="text-sm">
                  <span className="font-medium">{idx + 1}. {s.bin.code}</span>
                  <span className="text-slate-500"> — {s.bin.area}, {s.bin.fill_level}% full</span>
                </div>
                {s.status === 'pending' ? (
                  <button className="btn btn-primary text-xs" disabled={busy === s.id}
                          onClick={() => completeStop(s.id)}>
                    {busy === s.id ? 'Saving...' : 'Mark Collected'}
                  </button>
                ) : <StatusBadge status={s.status} />}
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  )
}
