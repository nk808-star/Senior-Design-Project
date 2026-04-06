-- Seed data aligned with NHANES mock (demographics, diseases, sample risk estimates).
-- Run after schema.sql. Replace with your real NHANES ETL when ready.

-- Filter options (NHANES-aligned)
INSERT INTO filter_options (filter_key, option_value) VALUES
  ('ethnicity', 'Mexican American'),
  ('ethnicity', 'Other Hispanic'),
  ('ethnicity', 'Non-Hispanic White'),
  ('ethnicity', 'Non-Hispanic Black'),
  ('ethnicity', 'Non-Hispanic Asian'),
  ('ethnicity', 'Non-Hispanic Other or Multiracial'),
  ('gender', 'Male'),
  ('gender', 'Female'),
  ('ageGroup', '18-24'),
  ('ageGroup', '25-34'),
  ('ageGroup', '35-44'),
  ('ageGroup', '45-54'),
  ('ageGroup', '55-64'),
  ('ageGroup', '65-74'),
  ('ageGroup', '75+'),
  ('socioeconomicStatus', 'PIR < 1.30 (low income)'),
  ('socioeconomicStatus', 'PIR 1.30–3.50 (middle income)'),
  ('socioeconomicStatus', 'PIR > 3.50 (higher income)'),
  ('socioeconomicStatus', 'Unknown/Refused'),
  ('diet', 'Low diet quality (HEI < 50)'),
  ('diet', 'Moderate diet quality (HEI 50–65)'),
  ('diet', 'High diet quality (HEI > 65)'),
  ('diet', 'Food insecure'),
  ('diet', 'Unknown/Not assessed')
ON CONFLICT (filter_key, option_value) DO NOTHING;

-- Diseases (NHANES-related outcomes)
INSERT INTO diseases (id, name, description) VALUES
  ('diabetes', 'Type 2 diabetes', 'From NHANES glucose/HbA1c and questionnaire (DIQ).'),
  ('hypertension', 'Hypertension', 'From NHANES blood pressure (BPX) and questionnaire (BPQ).'),
  ('cvd', 'Cardiovascular disease', 'From NHANES questionnaire (CDQ) and biomarkers.'),
  ('obesity', 'Obesity (BMI ≥ 30)', 'From NHANES body measures (BMX).'),
  ('kidney', 'Chronic kidney disease', 'From NHANES eGFR and albumin (KIQ).'),
  ('metabolic_syndrome', 'Metabolic syndrome', 'From NHANES waist, lipids, glucose, BP.')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description;

-- Sample risk assessments (mock NHANES-derived; one example per disease for a single cohort)
INSERT INTO risk_assessments (
  socioeconomic_status, ethnicity, gender, diet, age_group,
  disease_id, risk_level, score, confidence, model_version
) VALUES
  ('PIR < 1.30 (low income)', 'Non-Hispanic Black', 'Male', 'Low diet quality (HEI < 50)', '55-64', 'diabetes', 'moderate', 0.420, 0.85, 'nhanes-mock-v1'),
  ('PIR < 1.30 (low income)', 'Non-Hispanic Black', 'Male', 'Low diet quality (HEI < 50)', '55-64', 'hypertension', 'high', 0.510, 0.88, 'nhanes-mock-v1'),
  ('PIR < 1.30 (low income)', 'Non-Hispanic Black', 'Male', 'Low diet quality (HEI < 50)', '55-64', 'cvd', 'moderate', 0.380, 0.82, 'nhanes-mock-v1'),
  ('PIR < 1.30 (low income)', 'Non-Hispanic Black', 'Male', 'Low diet quality (HEI < 50)', '55-64', 'obesity', 'moderate', 0.520, 0.90, 'nhanes-mock-v1'),
  ('PIR < 1.30 (low income)', 'Non-Hispanic Black', 'Male', 'Low diet quality (HEI < 50)', '55-64', 'kidney', 'low', 0.260, 0.78, 'nhanes-mock-v1'),
  ('PIR < 1.30 (low income)', 'Non-Hispanic Black', 'Male', 'Low diet quality (HEI < 50)', '55-64', 'metabolic_syndrome', 'moderate', 0.430, 0.84, 'nhanes-mock-v1')
ON CONFLICT (socioeconomic_status, ethnicity, gender, diet, age_group, disease_id) DO UPDATE SET
  risk_level = EXCLUDED.risk_level,
  score = EXCLUDED.score,
  confidence = EXCLUDED.confidence,
  model_version = EXCLUDED.model_version;
