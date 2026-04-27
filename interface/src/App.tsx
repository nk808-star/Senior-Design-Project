import React, { useState, useEffect } from 'react';
import './App.css';

// --- Types ---
export interface RiskFilters {
  // Demographics & Socioeconomic
  ageGroup?: string;
  gender?: string;
  ethnicity?: string;
  socioeconomicStatus?: string;
  income?: string;
  insuranceStatus?: string;
  employmentStatus?: string;
  // Lifestyle
  smokingStatus?: string;
  alcoholUse?: string;
  physicalActivity?: string;
  diet?: string;
  // Metabolic & Cardiovascular
  bmi?: string;
  bloodGlucose?: string;
  hba1c?: string;
  insulin?: string;
  HDL?: string;
  LDL?: string;
  triglycerides?: string;
  crp?: string;
  // Renal & Kidney
  egfr?: string;
  creatinine?: string;
  BUN?: string;
  uricAcid?: string;
  albumin?: string;
  // Liver
  alt?: string;
  ast?: string;
  ggt?: string;
  // Blood Counts
  hemoglobin?: string;
  hct?: string;
  wbc?: string;
  // Electrolytes
  sodium?: string;
  potassium?: string;
  calcium?: string;
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

// --- Disease selector config ---
const ALL_DISEASES: { id: string; label: string }[] = [
  { id: 'gout',               label: 'Gout' },
  { id: 'diabetes',           label: 'Type 2 Diabetes' },
  { id: 'ckd',                label: 'Chronic Kidney Disease' },
  { id: 'hypertension',       label: 'Hypertension' },
  { id: 'cvd',                label: 'Cardiovascular Disease' },
  { id: 'metabolic_syndrome', label: 'Metabolic Syndrome' },
];

// --- Filter category config ---
const FILTER_SECTIONS: { label: string; keys: (keyof RiskFilters)[] }[] = [
  {
    label: 'Demographics & Socioeconomic',
    keys: ['ageGroup', 'gender', 'ethnicity', 'socioeconomicStatus', 'income', 'insuranceStatus', 'employmentStatus'],
  },
  {
    label: 'Lifestyle',
    keys: ['smokingStatus', 'alcoholUse', 'physicalActivity', 'diet'],
  },
  {
    label: 'Glucose & Insulin Metabolism',
    keys: ['bmi', 'bloodGlucose', 'hba1c', 'insulin'],
  },
  {
    label: 'Lipid Panel & Inflammation',
    keys: ['HDL', 'LDL', 'triglycerides', 'crp'],
  },
  {
    label: 'Renal Function',
    keys: ['egfr', 'creatinine', 'BUN', 'albumin', 'uricAcid'],
  },
  {
    label: 'Liver Enzymes',
    keys: ['alt', 'ast', 'ggt'],
  },
  {
    label: 'Complete Blood Count (CBC)',
    keys: ['hemoglobin', 'hct', 'wbc'],
  },
  {
    label: 'Electrolytes & Minerals',
    keys: ['sodium', 'potassium', 'calcium'],
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
  const [open, setOpen] = useState(false);
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

// --- Disease Selector ---
function DiseaseSelector({
  selected,
  onChange,
}: {
  selected: Set<string>;
  onChange: (id: string) => void;
}) {
  return (
    <div className="filter-section">
      <div className="section-header-static">
        <span className="section-label">Diseases to display</span>
      </div>
      <div className="section-body">
        {ALL_DISEASES.map(({ id, label }) => (
          <label key={id} className="disease-checkbox-row">
            <input
              type="checkbox"
              checked={selected.has(id)}
              onChange={() => onChange(id)}
            />
            <span>{label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

// --- Main App ---
function App() {
  const [activeFilters, setActiveFilters] = useState<RiskFilters>({});
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [riskData, setRiskData] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDiseases, setSelectedDiseases] = useState<Set<string>>(
    new Set(ALL_DISEASES.map((d) => d.id))
  );

  const toggleDisease = (id: string) => {
    setSelectedDiseases((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  useEffect(() => {
    fetch('/api/filters')
      .then((r) => r.json())
      .then((data: FilterOptions) => {
        setFilterOptions(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    Object.entries(activeFilters).forEach(([k, v]) => { if (v) params.append(k, v); });
    fetch(`/api/risk?${params.toString()}`)
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

          <DiseaseSelector selected={selectedDiseases} onChange={toggleDisease} />

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
            {riskData?.diseaseRisks.filter((r) => selectedDiseases.has(r.diseaseId)).map((risk) => (
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