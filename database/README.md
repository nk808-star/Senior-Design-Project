# Database

Placeholder schema for the medical information application backed by NHANES data and ML risk models.

## Contents

- **schema.sql** – Example tables for filter options, diseases, and risk assessments. Replace or extend with your own NHANES tables and ETL.
- **seed-nhanes-mock.sql** – NHANES-aligned mock seed data (filter options, diseases, sample risk assessments). Run after `schema.sql`.

## Integration

When you add your backend and database:

1. Map NHANES codebooks to `filter_options` (or serve filter options from your API).
2. Populate `diseases` with the conditions your models predict.
3. Fill `risk_assessments` from your ML pipeline (batch or on-demand), using the same filter dimensions the interface sends (socio-economic status, ethnicity, gender, diet, age group, etc.).

You can replace this with a different DB (e.g. MongoDB, DuckDB for analytics) and keep the same API contract used by the interface and backend.
