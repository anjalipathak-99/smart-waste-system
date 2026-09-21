import React from 'react'

export default function StatusBadge({ status }) {
  const cls = {
    normal: 'badge-normal',
    warning: 'badge-warning',
    critical: 'badge-critical',
    damaged: 'badge-damaged',
    pending: 'badge-warning',
    in_progress: 'bg-blue-100 text-blue-800',
    resolved: 'badge-normal',
    completed: 'badge-normal',
    low: 'badge-normal',
    medium: 'badge-warning',
    high: 'badge-critical',
  }[status] || 'bg-slate-100 text-slate-700'

  return <span className={`badge ${cls}`}>{status}</span>
}
