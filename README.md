# NHANES Medical Risk Explorer

A three-tier medical information application (interface, backend, database) that uses **NHANES**-aligned data to explore disease risk by demographics, socio-economic status, diet, and age. The UI provides filters and displays risk estimates; the backend currently uses mock NHANES-style data and can be replaced with your own NHANES pipeline and ML models.

## Clone and run

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

Then follow **Quick start** below.

## Structure

| Layer      | Folder       | Role |
|-----------|--------------|------|
| Interface | `interface/` | React (Vite) app: filters + disease risk cards. Calls backend API. |
| Backend   | `backend/`   | Express API stub: `/api/risk`, `/api/filters`. Replace with your NHANES + ML service. |
| Database  | `database/`  | Placeholder SQL schema. Replace with your NHANES/risk tables. |

## Quick start

### 1. Backend (stub runs with mock data)

```bash
cd backend
npm install
npm run dev
```

Runs at **http://localhost:8000**.

### 2. Interface

```bash
cd interface
npm install
npm run dev
```

Runs at **http://localhost:3000** and proxies `/api` to the backend.

### 3. Database

Use `database/schema.sql` as a reference. When you add your own DB, point the backend to it and replace the mock risk logic.

## API contract (for your backend)

The interface expects these endpoints. Implement them in your backend and keep the same request/response shapes.

### GET `/api/filters`

Returns options for each filter dropdown.

**Response:**

```json
{
  "socioeconomicStatus": ["Low", "Middle", "High", "..."],
  "ethnicity": ["White", "Black", "Hispanic", "..."],
  "gender": ["Male", "Female", "..."],
  "diet": ["Standard", "Vegetarian", "..."],
  "ageGroup": ["18-24", "25-34", "..."]
}
```

### GET `/api/risk?<filters>`

Query params: any combination of `socioeconomicStatus`, `ethnicity`, `gender`, `diet`, `ageGroup`.

**Response:**

```json
{
  "filters": { "gender": "Male", "ethnicity": "Hispanic", ... },
  "diseaseRisks": [
    {
      "diseaseId": "cvd",
      "diseaseName": "Cardiovascular disease",
      "riskLevel": "low | moderate | high | unknown",
      "score": 0.42,
      "confidence": 0.85,
      "description": "Optional short description."
    }
  ],
  "updatedAt": "2025-02-25T19:00:00.000Z"
}
```

When you plug in your NHANES pipeline and ML models, keep these field names and types so the existing UI works without changes.

## Environment

- **Interface:** optional `VITE_API_URL` (default `/api`). Set to your backend base URL if not using the Vite proxy.
- **Backend:** optional `PORT` (default `8000`).

## Next steps

1. Replace backend mock risk logic with your NHANES data and ML risk models.
2. Connect the backend to your database and use `database/schema.sql` (or your own schema) for filters and risk results.
3. Add or change filter dimensions in both backend and interface to match your NHANES variables and codebooks.

## License

This project is licensed under the MIT License—see [LICENSE](LICENSE).
