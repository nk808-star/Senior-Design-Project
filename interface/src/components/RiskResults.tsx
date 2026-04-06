import type { DiseaseRisk } from '../types'
import './RiskResults.css'

interface RiskResultsProps {
  risks: DiseaseRisk[]
  loading: boolean
}

const riskClass = (level: DiseaseRisk['riskLevel']) => {
  switch (level) {
    case 'low': return 'risk-low'
    case 'moderate': return 'risk-moderate'
    case 'high': return 'risk-high'
    default: return 'risk-unknown'
  }
}

export function RiskResults({ risks, loading }: RiskResultsProps) {
  if (loading) {
    return (
      <div className="risk-results">
        <h2 className="results-title">Disease risk assessment</h2>
        <div className="loading-state">Loading risk data…</div>
      </div>
    )
  }

  if (risks.length === 0) {
    return (
      <div className="risk-results">
        <h2 className="results-title">Disease risk assessment</h2>
        <div className="empty-state">
          <p>Set filters and click <strong>Update risk assessment</strong> to see disease risks.</p>
          <p className="hint">Results will appear here once the backend is connected.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="risk-results">
      <h2 className="results-title">Disease risk assessment</h2>
      <div className="risk-grid">
        {risks.map((r) => (
          <article key={r.diseaseId} className={`risk-card ${riskClass(r.riskLevel)}`}>
            <div className="risk-card-header">
              <h3>{r.diseaseName}</h3>
              <span className="risk-badge">{r.riskLevel}</span>
            </div>
            {r.score != null && (
              <div className="risk-score">
                Score: <code>{r.score.toFixed(2)}</code>
                {r.confidence != null && (
                  <span className="confidence"> (confidence: {(r.confidence * 100).toFixed(0)}%)</span>
                )}
              </div>
            )}
            {r.description && <p className="risk-desc">{r.description}</p>}
          </article>
        ))}
      </div>
    </div>
  )
}
