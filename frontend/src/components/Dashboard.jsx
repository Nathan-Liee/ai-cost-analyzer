import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'
import '../styles/Dashboard.css'

export default function Dashboard() {
  const [file, setFile] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleUpload = async (e) => {
    const f = e.target.files[0]
    if (!f) return

    setFile(f)
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', f)
    formData.append('user_id', 'test_user')

    try {
      const res = await fetch('http://localhost:8000/api/recommendations', {
        method: 'POST',
        body: formData
      }).catch(() => {
        throw new Error('Cannot connect to backend. Make sure backend is running.')
      })
      
      if (!res.ok) throw new Error('Upload failed')
      
      const data = await res.json()
      setAnalysis(data.analysis)
      setRecommendations(data.recommendations || [])
    } catch (err) {
      setError('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!analysis) {
    return (
      <div className="container">
        <header className="header">
          <h1>💰 AI Cost Analyzer</h1>
          <p>Track and optimize your API spending</p>
        </header>

        <div className="upload-section">
          <div className="upload-box">
            <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <h2>Upload Your API Logs</h2>
            <p>Supported formats: CSV, JSON</p>
            <input 
              type="file" 
              accept=".csv,.json"
              onChange={handleUpload}
              disabled={loading}
              className="file-input"
            />
            {loading && <p className="loading">📊 Analyzing...</p>}
            {error && <p className="error">❌ {error}</p>}
          </div>
        </div>
      </div>
    )
  }

  const chartData = Object.entries(analysis.by_model).map(([model, data]) => ({
    name: model,
    cost: parseFloat(data.cost),
    tokens: data.tokens
  }))

  const totalSavings = recommendations.reduce((sum, rec) => sum + rec.savings, 0)

  return (
    <div className="container">
      <header className="header">
        <h1>💰 AI Cost Analyzer</h1>
        <p>Your API spending insights</p>
      </header>

      <div className="summary-section">
        <div className="summary-card total">
          <h3>Total Spending</h3>
          <p className="amount">${analysis.total_cost.toFixed(2)}</p>
          <small>{analysis.count} logs analyzed</small>
        </div>
        
        {totalSavings > 0 && (
          <div className="summary-card savings">
            <h3>Potential Savings</h3>
            <p className="amount">${totalSavings.toFixed(2)}</p>
            <small>from recommendations</small>
          </div>
        )}
      </div>

      <div className="chart-section">
        <h2>Cost Breakdown by Model</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
            <Legend />
            <Bar dataKey="cost" fill="#8884d8" name="Cost ($)" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {recommendations.length > 0 && (
        <div className="recommendations-section">
          <h2>💡 Optimization Recommendations</h2>
          <div className="recommendations-grid">
            {recommendations.map((rec, idx) => (
              <div key={idx} className={`recommendation-card priority-${rec.priority}`}>
                <div className="rec-header">
                  <h3>{rec.description}</h3>
                  <span className={`priority-badge ${rec.priority}`}>{rec.priority}</span>
                </div>
                <p className="savings">
                  💰 Save: <strong>${rec.savings.toFixed(2)}</strong> ({rec.savings_percent}%)
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="details-section">
        <h2>Detailed Breakdown</h2>
        <div className="details-grid">
          {chartData.map(item => (
            <div key={item.name} className="detail-card">
              <h4>{item.name}</h4>
              <div className="detail-row">
                <span>Cost</span>
                <strong>${item.cost.toFixed(4)}</strong>
              </div>
              <div className="detail-row">
                <span>Tokens</span>
                <strong>{item.tokens.toLocaleString()}</strong>
              </div>
              <div className="detail-row">
                <span>% of Total</span>
                <strong>{((item.cost / analysis.total_cost) * 100).toFixed(1)}%</strong>
              </div>
            </div>
          ))}
        </div>
      </div>

      <button className="action-btn" onClick={() => {
        setAnalysis(null)
        setRecommendations([])
        setFile(null)
      }}>
        ↺ Analyze Another File
      </button>
    </div>
  )
}
