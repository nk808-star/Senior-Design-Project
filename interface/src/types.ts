/** Filter values sent to the backend; extend when your API is ready. */
export interface RiskFilters {
  socioeconomicStatus?: string;
  ethnicity?: string;
  gender?: string;
  diet?: string;
  ageGroup?: string;
  physicalActivity?: string;
  smokingStatus?: string;
  [key: string]: string | undefined;
}

/** Disease risk item returned by the backend. */
export interface DiseaseRisk {
  diseaseId: string;
  diseaseName: string;
  riskLevel: 'low' | 'moderate' | 'high' | 'unknown';
  score?: number;
  confidence?: number;
  description?: string;
}

/** Response shape for the risk assessment API. */
export interface RiskResponse {
  filters: RiskFilters;
  diseaseRisks: DiseaseRisk[];
  updatedAt?: string;
}

/** Options for filter dropdowns (can be replaced by backend later). */
export interface FilterOptions {
  socioeconomicStatus: string[];
  ethnicity: string[];
  gender: string[];
  diet: string[];
  ageGroup: string[];
}
