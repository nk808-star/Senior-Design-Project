import React, { useState, useEffect } from 'react';
import './App.css';

// --- Types ---
export interface RiskFilters {
  // Demographics & Socioeconomic
  ageGroup?: string;
  gender?: string;
  ethnicity?: string;
  incomeLevel?: string;
  education?: string;
  insuranceStatus?: string;
  // Cardiovascular Biomarkers
  bloodPressure?: string;
  totalCholesterol?: string;
  ldlCholesterol?: string;
  hdlCholesterol?: string;
  triglycerides?: string;
  // Metabolic Biomarkers
  fastingGlucose?: string;
  hba1c?: string;
  bmi?: string;
  creatinine?: string;
  uricAcid?: string;
  // Lifestyle
  smokingStatus?: string;
  alcoholUse?: string;
  physicalActivity?: string;
  diet?: string;
  [key: string]: string | undefined;
}

export interface DiseaseRisk {
  diseaseId: string;
  diseaseName: string;
  riskLevel: 'low' | 'moderate' | 'high' | 'unknown';
  score?: number;
  confidence?: number;
  description?: string;
}

export interface RiskResponse {
  filters: RiskFilters;
  diseaseRisks: DiseaseRisk[];
  updatedAt?: string;
}

export interface FilterOptions {
  [key: string]: string[];
}

// --- Filter category config ---
// Add/remove/rename keys here to match whatever your backend returns
const FILTER_SECTIONS: { label: string; keys: (keyof RiskFilters)[] }[] = [
  {
    label: 'Demographics & socioeconomic',
    keys: ['ageGroup', 'gender', 'ethnicity', 'incomeLevel', 'education', 'insuranceStatus'],
  },
  {
    label: 'Lifestyle',
    keys: ['smokingStatus', 'alcoholUse', 'physicalActivity', 'diet'],
  },
  {
    label: 'Renal & Kidney Function',
    keys: ['uricAcid', 'creatinine', 'egfr', 'BUN', 'albumin', 'acr', 'urineUricAcid'],
  },
  {
    label: 'Metabolic & Cardiovascular',
    keys: ['bmi', 'bloodGlucose', 'hba1c', 'insulin', 'HDL', 'LDL', 'triglycerides', 'crp'],
  },
];

function toLabel(key: string): string {
  return key
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (s) => s.toUpperCase())
    .trim();
}

function ActiveFilterSummary({ filters }: { filters: RiskFilters }) {
  const active = Object.entries(filters).filter(([, v]) => v);
  if (!active.length) return <span className="summary-empty">No filters applied</span>;
  return (
    <span className="summary-tags">
      {active.map(([k, v]) => (
        <span key={k} className="summary-tag">{toLabel(k)}: {v}</span>
      ))}
    </span>
  );
}

// --- Collapsible Section ---
function FilterSection({
  label,
  keys,
  filterOptions,
  activeFilters,
  onChange,
}: {
  label: string;
  keys: (keyof RiskFilters)[];
  filterOptions: FilterOptions;
  activeFilters: RiskFilters;
  onChange: (key: keyof RiskFilters, value: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const activeCount = keys.filter((k) => activeFilters[k]).length;

  return (
    <div className="filter-section">
      <button className="section-header" onClick={() => setOpen((o) => !o)}>
        <span className="section-left">
          <span className="section-label">{label}</span>
          {activeCount > 0 && <span className="badge badge-active">{activeCount}</span>}
        </span>
        <svg
          className={`chevron ${open ? 'open' : ''}`}
          width="12" height="12" viewBox="0 0 12 12" fill="none"
        >
          <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {open && (
        <div className="section-body">
          {keys.map((key) => {
            const options = filterOptions[key as string];
            if (!options) return null;
            const isSet = !!activeFilters[key];
            return (
              <div key={key as string} className="filter-row">
                <label className="filter-label">{toLabel(key as string)}</label>
                <select
                  className={`filter-select ${isSet ? 'is-set' : ''}`}
                  value={activeFilters[key] || ''}
                  onChange={(e) => onChange(key, e.target.value)}
                >
                  <option value="">All categories</option>
                  {options.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// --- Main App ---
function App() {
  const [activeFilters, setActiveFilters] = useState<RiskFilters>({});
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [riskData, setRiskData] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState(true);

 useEffect(() => {
  fetch('http://localhost:8000/api/filters')
    .then((r) => r.json())
    .then((data: FilterOptions) => { 
      console.log("RAW NHANES DATA:", data); 
      setFilterOptions(data); 
      setLoading(false); 
    })
    .catch(() => setLoading(false));
}, []);

  useEffect(() => {
    const params = new URLSearchParams();
    Object.entries(activeFilters).forEach(([k, v]) => { if (v) params.append(k, v); });
    fetch(`http://localhost:8000/api/risk?${params.toString()}`)
      .then((r) => r.json())
      .then((data: RiskResponse) => setRiskData(data))
      .catch(console.error);
  }, [activeFilters]);

  const handleChange = (key: keyof RiskFilters, value: string) => {
    setActiveFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearAll = () => setActiveFilters({});

  const totalActive = Object.values(activeFilters).filter(Boolean).length;

  if (loading) return <div className="loading">Connecting to NHANES database…</div>;

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>NHANES Medical Risk Explorer</h1>
      </header>

      <div className="app-body">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-top">
            <span className="sidebar-title">Patient filters</span>
            {totalActive > 0 && (
              <button className="clear-btn" onClick={clearAll}>Clear all ({totalActive})</button>
            )}
          </div>

          {filterOptions && FILTER_SECTIONS.map((section) => (
            <FilterSection
              key={section.label}
              label={section.label}
              keys={section.keys}
              filterOptions={filterOptions}
              activeFilters={activeFilters}
              onChange={handleChange}
            />
          ))}
        </aside>

        {/* Main content */}
        <main className="main-content">
          <div className="results-header">
            <h2>Risk assessment</h2>
            <div className="active-summary">
              <ActiveFilterSummary filters={activeFilters} />
            </div>
          </div>

          <div className="risk-grid">
            {riskData?.diseaseRisks.map((risk) => (
              <div key={risk.diseaseId} className={`risk-card risk-${risk.riskLevel}`}>
                <div className="risk-card-header">
                  <h3>{risk.diseaseName}</h3>
                  <span className={`risk-badge risk-badge-${risk.riskLevel}`}>{risk.riskLevel}</span>
                </div>
                <div className="risk-score-row">
                  <span className="score-num">{((risk.score ?? 0) * 100).toFixed(0)}%</span>
                  <span className="score-label">risk score</span>
                </div>
                {risk.description && <p className="risk-desc">{risk.description}</p>}
                <div className="confidence-row">
                  <span>Confidence</span>
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{ width: `${((risk.confidence ?? 0) * 100).toFixed(0)}%` }}
                    />
                  </div>
                  <span>{((risk.confidence ?? 0) * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;