# NHANES Medical Risk Explorer

A full-stack web application that predicts disease risk for six chronic conditions using real NHANES (National Health and Nutrition Examination Survey) population data and a K-Nearest Neighbors ML model.

---

## What it does

Users select patient biomarkers and demographic filters in the UI (age, BMI, cholesterol, uric acid, etc.) and the app returns risk scores for:

- **Gout** *(primary focus)*
- Type 2 Diabetes
- Chronic Kidney Disease (CKD)
- Hypertension
- Cardiovascular Disease (CVD)
- Metabolic Syndrome

Risk scores are produced by KNN classifiers trained on real NHANES survey data from 1999–2018 (~100,000 participants across 10 survey cycles). Labels are inferred from clinical thresholds — not self-reported — making this a genuine risk prediction tool.

---

## Project structure

```
├── backend/
│   ├── nhanes_api.py          # Flask API — /api/filters and /api/risk endpoints
│   ├── ml_model.py            # Loads trained KNN models, encodes UI filters, returns predictions
│   ├── build_dataset.py       # Downloads NHANES data, builds feature/label CSVs
│   ├── train_knn.py           # Trains KNN per disease, sweeps K=1..15 via DICE score
│   ├── validate_model.py      # 5-fold cross validation, ROC curves, performance report
│   ├── patient_profile_builder.py
│   ├── download_nhanes_file.py
│   ├── requirements.txt
│   ├── data/                  # Created automatically — cached NHANES XPT files + CSVs
│   └── models/                # Created automatically — trained .pkl model files
├── interface/
│   ├── src/
│   │   ├── App.tsx            # Main React app — filter sidebar + risk card grid
│   │   ├── App.css
│   │   └── types.ts
│   └── package.json
└── database/
    └── schema.sql
```

---

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**

---

## Setup

### 1. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd interface
npm install
```

---

## Running the app (after models are trained)

If someone on your team has already trained the models and shared the `backend/models/` folder with you, skip to this step.

**Terminal 1 — start the backend:**
```bash
cd backend
python nhanes_api.py
```
Runs at `http://localhost:8000`

**Terminal 2 — start the frontend:**
```bash
cd interface
npm run dev
```
Runs at `http://localhost:5173` (or `3000`). Open this in your browser.

---

## Training the ML model (first-time setup)

This only needs to be done once, or whenever you want to retrain with updated data.

### Step 1 — Build the dataset

Downloads NHANES XPT files from the CDC website, merges them, and saves feature/label CSVs to `backend/data/`.

```bash
cd backend
python build_dataset.py
```

> **Note:** This downloads ~130 files (~500 MB total) and takes 10–20 minutes the first time. Files are cached locally so re-runs are instant.

### Step 2 — Train the KNN models

Trains one KNN classifier per disease using scaled Euclidean distance. Sweeps K = 1–15 and picks the K that maximises the DICE score on a held-out test set (25%). Saves trained models to `backend/models/`.

```bash
python train_knn.py
```

Output will show the optimal K and DICE/IoU/Accuracy for each disease. DICE optimisation plots are saved to `backend/models/` as PNG files.

### Step 3 *(optional)* — Validate the models

Runs 5-fold stratified cross validation on each disease model and generates a full performance report. Useful for evaluating model quality or including results in a report.

```bash
python validate_model.py
```

Outputs saved to `backend/models/`:
- `validation_report.txt` — summary table with DICE, AUC, Sensitivity, Specificity, PPV, and Accuracy per disease (mean ± std across folds)
- `{disease}_roc_curve.png` — ROC curve per disease (one PNG per disease)

**Reading the results:**

| Metric | What it means |
|---|---|
| DICE | Balance between catching real cases and avoiding false alarms |
| AUC | Overall discrimination — 0.5 = random, 1.0 = perfect; >0.75 is good |
| Sensitivity | % of actual cases correctly flagged (low = missing sick people) |
| Specificity | % of healthy people correctly cleared (low = over-diagnosing) |
| PPV | When the model says "high risk", how often it is correct |
| Accuracy | Overall correct predictions (can be misleading for rare diseases) |

### Step 4 — Start the app

Follow the **Running the app** steps above.

---

## How the ML model works

### Data

NHANES surveys ~10,000 Americans every two years. This app uses 10 survey cycles (1999–2018), giving ~100,000 participants. Variables include demographics, biomarkers, lifestyle factors, and physical exam measurements.

### Feature encoding

Continuous biomarker values (e.g. BMI = 32.5 kg/m²) are binned into the same categorical ranges shown in the UI dropdowns (e.g. "Obese (≥30)"). This ensures the training data and the user's filter selections use the same representation.

### Label inference

Disease labels are **inferred from biomarker thresholds**, not taken from self-reported questionnaires:

| Disease | Inference criterion |
|---|---|
| Gout | Serum uric acid ≥ 7.0 mg/dL (men) / 6.0 mg/dL (women) |
| Type 2 Diabetes | Fasting glucose ≥ 126 mg/dL OR HbA1c ≥ 6.5% |
| CKD | Calculated eGFR < 60 mL/min/1.73m² (CKD-EPI equation) |
| Hypertension | SBP ≥ 130 mmHg OR DBP ≥ 80 mmHg (ACC/AHA 2017) |
| CVD | 3+ of: high LDL, low HDL, smoking, age ≥55, diabetes, high CRP, high triglycerides |
| Metabolic Syndrome | 3+ ATP III criteria (waist, triglycerides, HDL, BP, glucose) |

### KNN classifier

The model uses **scaled Euclidean (seuclidean) distance**, which normalises each feature by its variance so biomarkers with different scales contribute equally. This is equivalent to MATLAB's `createns(..., 'Distance', 'seuclidean')`.

At inference time, the model finds the K most similar NHANES participants to the user's filter profile and returns the fraction who met the disease threshold — that fraction is the risk score shown in the UI.

### Confidence score

The confidence bar reflects how many filters the user has filled in. More inputs → more specific neighbor matching → higher confidence (scales from 45% with no inputs to 95% with all inputs).

---

## Adding more NHANES data

To include additional survey cycles, edit the `CYCLES` list at the top of `backend/build_dataset.py`:

```python
CYCLES = [
    {"year": "2017", "suffix": "_J", "label": "2017-2018"},
    {"year": "2015", "suffix": "_I", "label": "2015-2016"},
    # add more entries here ...
]
```

Then re-run `build_dataset.py` and `train_knn.py`.

---

## API reference

### `GET /api/filters`
Returns the dropdown options for every filter in the UI.

### `GET /api/risk`
Accepts any combination of filter query parameters and returns risk scores for all six diseases.

**Example request:**
```
GET /api/risk?gender=Male&ageGroup=45-54&uricAcid=High+(%3E7.2)&bmi=Obese+(>=30)
```

**Example response:**
```json
{
  "filters": { "gender": "Male", "ageGroup": "45-54" },
  "diseaseRisks": [
    {
      "diseaseId": "gout",
      "diseaseName": "Gout",
      "riskLevel": "high",
      "score": 0.74,
      "confidence": 0.62,
      "description": "Risk inferred from serum uric acid levels and metabolic profile."
    }
  ],
  "updatedAt": "2026-04-23T14:00:00Z"
}
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, Flask, Flask-CORS |
| ML | scikit-learn (KNeighborsClassifier), pandas, numpy |
| Data | NHANES public data (CDC) — 1999–2018 |

---

## License

MIT
