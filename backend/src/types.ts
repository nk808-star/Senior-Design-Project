export interface RiskFilters {
  socioeconomicStatus?: string;
  ethnicity?: string;
  gender?: string;
  diet?: string;
  ageGroup?: string;
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
  socioeconomicStatus: string[];
  ethnicity: string[];
  gender: string[];
  diet: string[];
  ageGroup: string[];
}
