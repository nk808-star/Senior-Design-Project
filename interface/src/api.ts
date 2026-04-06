import type { RiskFilters, RiskResponse, FilterOptions } from './types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Fetch disease risk assessment based on current filters. */
export async function fetchRiskAssessment(filters: RiskFilters): Promise<RiskResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v != null && v !== '') params.set(k, v);
  });
  const qs = params.toString();
  return request<RiskResponse>(`/risk?${qs}`);
}

/** Fetch available filter options (e.g. for dropdowns). Can be replaced by your backend. */
export async function fetchFilterOptions(): Promise<FilterOptions> {
  try {
    return await request<FilterOptions>('/filters');
  } catch {
    return getDefaultFilterOptions();
  }
}

function getDefaultFilterOptions(): FilterOptions {
  return {
    socioeconomicStatus: ['Low', 'Middle', 'High', 'Prefer not to say'],
    ethnicity: ['White', 'Black', 'Hispanic', 'Asian', 'Other', 'Prefer not to say'],
    gender: ['Male', 'Female', 'Other', 'Prefer not to say'],
    diet: ['Standard', 'Vegetarian', 'Vegan', 'Low-carb', 'Mediterranean', 'Other'],
    ageGroup: ['18-24', '25-34', '35-44', '45-54', '55-64', '65+'],
  };
}
