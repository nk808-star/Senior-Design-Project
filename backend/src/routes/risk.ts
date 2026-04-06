import { Router, Request } from 'express';
import type { RiskResponse } from '../types.js';
import { getMockDiseaseRisks } from '../data/nhanesMock.js';

export const riskRouter = Router();

/** GET /api/risk?gender=...&ethnicity=... etc. Uses NHANES-style mock data. */
riskRouter.get('/risk', (req: Request<object, RiskResponse, unknown, Record<string, string>>, res) => {
  const filters = req.query as Record<string, string>;
  const diseaseRisks = getMockDiseaseRisks(filters);
  const response: RiskResponse = {
    filters: { ...filters },
    diseaseRisks,
    updatedAt: new Date().toISOString(),
  };
  res.json(response);
});
