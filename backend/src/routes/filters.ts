import { Router } from 'express';
import { NHANES_FILTER_OPTIONS } from '../data/nhanesMock.js';

export const filtersRouter = Router();

/** GET /api/filters - NHANES-aligned options for filter dropdowns. */
filtersRouter.get('/filters', (_req, res) => {
  res.json(NHANES_FILTER_OPTIONS);
});
