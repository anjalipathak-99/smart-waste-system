import React, { useState } from 'react'
import api from '../api/client'

const CLASS_COLORS = {
  Plastic: '#3b82f6', Paper: '#a16207', Metal: '#64748b', Glass: '#06b6d4',
  Organic: '#16a34a', 'E-waste': '#dc2626', Other: '#9333ea',
}

export default function ClassifyWaste() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = (e) => {
    const f = e.target.files[0]
    if (!f) return
    setFile(f)
    setResult(null)
    setPreview(URL.createObjectURL(f))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('image', file)
      const res = await api.post('/classify', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.error || 'Classification failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">AI Waste Classification</h1>
      <p className="text-slate-500 text-sm">
        Upload a photo of a waste item and the AI model will classify it as Plastic, Paper, Metal,
        Glass, Organic, E-waste, or Other.
      </p>

      <form onSubmit={handleSubmit} className="card space-y-4">
        <input type="file" accept="image/*" onChange={handleFile} className="block text-sm" />
        {preview && <img src={preview} alt="preview" className="max-h-64 rounded-lg border" />}
        <button className="btn btn-primary" disabled={!file || loading}>
          {loading ? 'Classifying...' : 'Classify Image'}
        </button>
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </form>

      {result && (
        <div className="card">
          <h3 className="font-semibold text-slate-700 mb-3">Result</h3>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl font-bold" style={{ color: CLASS_COLORS[result.predicted_class] }}>
              {result.predicted_class}
            </span>
            <span className="text-slate-500">({(result.confidence * 100).toFixed(1)}% confidence)</span>
          </div>
          <div className="space-y-1">
            {Object.entries(result.all_probabilities)
              .sort((a, b) => b[1] - a[1])
              .map(([cls, prob]) => (
                <div key={cls} className="flex items-center gap-2 text-sm">
                  <span className="w-20 text-slate-600">{cls}</span>
                  <div className="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div className="h-3 rounded-full" style={{ width: `${prob * 100}%`, backgroundColor: CLASS_COLORS[cls] }} />
                  </div>
                  <span className="w-12 text-right text-slate-500">{(prob * 100).toFixed(1)}%</span>
                </div>
              ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">Model: {result.model_used}</p>
        </div>
      )}
    </div>
  )
}
