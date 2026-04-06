import type { RiskFilters, FilterOptions } from '../types'
import './FilterPanel.css'

interface FilterPanelProps {
  filters: RiskFilters
  options: FilterOptions | null
  onChange: (f: RiskFilters) => void
  onApply: () => void
  loading: boolean
}

const FILTER_KEYS = [
  { key: 'socioeconomicStatus', label: 'Socio-economic status' },
  { key: 'ethnicity', label: 'Ethnicity' },
  { key: 'gender', label: 'Gender' },
  { key: 'diet', label: 'Diet' },
  { key: 'ageGroup', label: 'Age group' },
] as const

export function FilterPanel({ filters, options, onChange, onApply, loading }: FilterPanelProps) {
  const update = (key: string, value: string) => {
    onChange({ ...filters, [key]: value || undefined })
  }

  return (
    <div className="filter-panel">
      <h2 className="filter-panel-title">Filters</h2>
      <p className="filter-panel-desc">Adjust to see risk estimates for your profile.</p>

      {FILTER_KEYS.map(({ key, label }) => (
        <div key={key} className="filter-field">
          <label htmlFor={key}>{label}</label>
          <select
            id={key}
            value={filters[key] ?? ''}
            onChange={(e) => update(key, e.target.value)}
            disabled={!options}
          >
            <option value="">Any</option>
            {(options?.[key as keyof FilterOptions] ?? []).map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      ))}

      <button
        type="button"
        className="apply-btn"
        onClick={onApply}
        disabled={loading}
      >
        {loading ? 'Loading…' : 'Update risk assessment'}
      </button>
    </div>
  )
}
