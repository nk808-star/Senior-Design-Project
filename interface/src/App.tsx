import { useState, useEffect, useCallback } from 'react'
import type { RiskFilters, DiseaseRisk, FilterOptions } from './types'
import { fetchRiskAssessment, fetchFilterOptions } from './api'
import { FilterPanel } from './components/FilterPanel'
import { RiskResults } from './components/RiskResults'
import './App.css'

export default function App() {
  const [filters, setFilters] = useState<RiskFilters>({})
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null)
  const [risks, setRisks] = useState<DiseaseRisk[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFilterOptions().then(setFilterOptions)
  }, [])

  const loadRisks = useCallback(async () => {
    setError(null)
    setLoading(true)
    try {
      const res = await fetchRiskAssessment(filters)
      setRisks(res.diseaseRisks ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load risk data')
      setRisks([])
    } finally {
      setLoading(false)
    }
  }, [filters])

  return (
    <div className="app">
      <header className="app-header">
        <h1>NHANES Medical Risk Explorer</h1>
        <p className="tagline">Disease risk insights from NHANES data and ML models</p>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <FilterPanel
            filters={filters}
            options={filterOptions}
            onChange={setFilters}
            onApply={loadRisks}
            loading={loading}
          />
        </aside>

        <main className="main">
          {error && (
            <div className="banner error">
              {error}
            </div>
          )}
          <RiskResults risks={risks} loading={loading} />
        </main>
      </div>
    </div>
  )
}
