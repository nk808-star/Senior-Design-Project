import express from 'express';
import cors from 'cors';
import { riskRouter } from './routes/risk.js';
import { filtersRouter } from './routes/filters.js';

const app = express();
const PORT = process.env.PORT ?? 8000;

app.use(cors({ origin: true }));
app.use(express.json());

// Mount under /api so frontend proxy works
app.use('/api', riskRouter);
app.use('/api', filtersRouter);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', service: 'medical-info-backend' });
});

app.listen(PORT, () => {
  console.log(`Backend running at http://localhost:${PORT}`);
});
