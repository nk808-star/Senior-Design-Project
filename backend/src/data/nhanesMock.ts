/**
 * Mock data aligned with NHANES (National Health and Nutrition Examination Survey).
 * Demographics, socioeconomic, and diet categories follow NHANES codebooks.
 * Risk estimates are synthetic and for demo only; replace with your ML/NHANES pipeline.
 */

import type { FilterOptions, DiseaseRisk } from '../types.js';

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/** NHANES-aligned filter options (DEMO, questionnaire codebooks). */
export const NHANES_FILTER_OPTIONS: FilterOptions = {
  // RIDRETH1 / RIDRETH3: Race/Hispanic origin
  ethnicity: [
    'Mexican American',
    'Other Hispanic',
    'Non-Hispanic White',
    'Non-Hispanic Black',
    'Non-Hispanic Asian',
    'Non-Hispanic Other or Multiracial',
  ],
  // RIAGEND: Gender
  gender: ['Male', 'Female'],
  // Age groups (NHANES uses RIDAGEYR; grouped for analysis)
  ageGroup: [
    '18-24',
    '25-34',
    '35-44',
    '45-54',
    '55-64',
    '65-74',
    '75+',
  ],
  // Poverty Income Ratio (INDFMPIR) / family income categories
  socioeconomicStatus: [
    'PIR < 1.30 (low income)',
    'PIR 1.30–3.50 (middle income)',
    'PIR > 3.50 (higher income)',
    'Unknown/Refused',
  ],
  // Diet quality / food security (FSDHH / HEI-style categories from dietary data)
  diet: [
    'Low diet quality (HEI < 50)',
    'Moderate diet quality (HEI 50–65)',
    'High diet quality (HEI > 65)',
    'Food insecure',
    'Unknown/Not assessed',
  ],
};

/** Disease outcomes commonly analyzed in NHANES (diabetes, hypertension, CVD, obesity, kidney). */
const DISEASE_IDS = [
  { id: 'diabetes', name: 'Type 2 diabetes', description: 'From NHANES glucose/HbA1c and questionnaire (DIQ).' },
  { id: 'hypertension', name: 'Hypertension', description: 'From NHANES blood pressure (BPX) and questionnaire (BPQ).' },
  { id: 'cvd', name: 'Cardiovascular disease', description: 'From NHANES questionnaire (CDQ) and biomarkers.' },
  { id: 'obesity', name: 'Obesity (BMI ≥ 30)', description: 'From NHANES body measures (BMX).' },
  { id: 'kidney', name: 'Chronic kidney disease', description: 'From NHANES eGFR and albumin (KIQ).' },
  { id: 'metabolic_syndrome', name: 'Metabolic syndrome', description: 'From NHANES waist, lipids, glucose, BP.' },
] as const;

type RiskLevel = 'low' | 'moderate' | 'high' | 'unknown';

/** Deterministic mock risk from filters (NHANES-inspired patterns; replace with real model). */
function mockRiskScore(
  diseaseId: string,
  filters: Record<string, string>
): { score: number; riskLevel: RiskLevel; confidence: number } {
  let base = 0.2;
  const ethnicity = filters.ethnicity ?? '';
  const gender = filters.gender ?? '';
  const ageGroup = filters.ageGroup ?? '';
  const socioeconomicStatus = filters.socioeconomicStatus ?? '';
  const diet = filters.diet ?? '';

  // Age effect (older → higher risk for most conditions)
  const ageFactor = ageGroup.includes('65') || ageGroup === '75+' ? 0.25 : ageGroup.includes('55') ? 0.18 : ageGroup.includes('45') ? 0.10 : 0;
  // Socioeconomic (lower PIR → higher risk in NHANES)
  const pirFactor = socioeconomicStatus.includes('< 1.30') ? 0.15 : socioeconomicStatus.includes('1.30') ? 0.06 : 0;
  // Diet (low quality or food insecure → higher risk)
  const dietFactor = diet.includes('Low') || diet.includes('insecure') ? 0.12 : diet.includes('Moderate') ? 0.05 : 0;

  switch (diseaseId) {
    case 'diabetes':
      base = 0.22;
      if (ethnicity.includes('Hispanic') || ethnicity.includes('Black')) base += 0.08;
      if (ageFactor > 0.15) base += 0.12;
      break;
    case 'hypertension':
      base = 0.28;
      if (ethnicity.includes('Black')) base += 0.10;
      if (gender === 'Male') base += 0.03;
      break;
    case 'cvd':
      base = 0.18;
      if (ageFactor > 0.15) base += 0.14;
      if (socioeconomicStatus.includes('< 1.30')) base += 0.08;
      break;
    case 'obesity':
      base = 0.35;
      if (ethnicity.includes('Black')) base += 0.06;
      if (diet.includes('Low') || diet.includes('insecure')) base += 0.05;
      break;
    case 'kidney':
      base = 0.12;
      if (ageFactor > 0.18) base += 0.10;
      if (ethnicity.includes('Black')) base += 0.04;
      break;
    case 'metabolic_syndrome':
      base = 0.25;
      if (ageFactor > 0.10) base += 0.10;
      if (diet.includes('Low')) base += 0.08;
      break;
    default:
      base = 0.20;
  }

  let score = base + ageFactor + pirFactor + dietFactor;
  score = Math.min(0.95, Math.max(0.05, score));
  const confidence = 0.78 + ((hashCode(diseaseId + JSON.stringify(filters)) % 13) / 100);

  let riskLevel: RiskLevel = 'unknown';
  if (score >= 0.55) riskLevel = 'high';
  else if (score >= 0.35) riskLevel = 'moderate';
  else if (score > 0) riskLevel = 'low';

  return { score, riskLevel, confidence };
}

/** Build disease risks from current filters using NHANES-style mock logic. */
export function getMockDiseaseRisks(filters: Record<string, string>): DiseaseRisk[] {
  return DISEASE_IDS.map((d) => {
    const { score, riskLevel, confidence } = mockRiskScore(d.id, filters);
    return {
      diseaseId: d.id,
      diseaseName: d.name,
      riskLevel,
      score: Math.round(score * 1000) / 1000,
      confidence: Math.round(confidence * 1000) / 1000,
      description: d.description,
    };
  });
}
