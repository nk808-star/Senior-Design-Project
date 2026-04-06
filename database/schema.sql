-- Placeholder schema for NHANES-based medical risk application.
-- Replace and extend when you connect your own NHANES + ML pipeline.

-- Example: store filter dimensions (can be driven by NHANES codebooks)
CREATE TABLE IF NOT EXISTS filter_options (
  id          SERIAL PRIMARY KEY,
  filter_key  VARCHAR(64) NOT NULL,
  option_value VARCHAR(256) NOT NULL,
  UNIQUE (filter_key, option_value)
);

-- Example: disease definitions (your ML models may output risk per disease_id)
CREATE TABLE IF NOT EXISTS diseases (
  id          VARCHAR(32) PRIMARY KEY,
  name        VARCHAR(256) NOT NULL,
  description TEXT
);

-- Example: risk assessment results (e.g. from batch ML jobs or on-demand)
-- Adjust columns to match your NHANES variables and model outputs
CREATE TABLE IF NOT EXISTS risk_assessments (
  id            SERIAL PRIMARY KEY,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  -- Filter / cohort dimensions (align with NHANES and your filters)
  socioeconomic_status VARCHAR(64),
  ethnicity      VARCHAR(64),
  gender         VARCHAR(32),
  diet           VARCHAR(64),
  age_group      VARCHAR(32),
  -- Add more NHANES-derived dimensions as needed
  disease_id     VARCHAR(32) NOT NULL REFERENCES diseases(id),
  risk_level     VARCHAR(16) NOT NULL CHECK (risk_level IN ('low', 'moderate', 'high', 'unknown')),
  score         DECIMAL(5,4),
  confidence    DECIMAL(5,4),
  model_version VARCHAR(64),
  UNIQUE (socioeconomic_status, ethnicity, gender, diet, age_group, disease_id)
);

-- Index for fast lookups by filter combination
CREATE INDEX IF NOT EXISTS idx_risk_filters ON risk_assessments (
  socioeconomic_status, ethnicity, gender, diet, age_group
);

-- Example: raw NHANES variable mapping (placeholder for your ETL)
-- CREATE TABLE nhanes_variables (...);
-- CREATE TABLE nhanes_survey_data (...);
