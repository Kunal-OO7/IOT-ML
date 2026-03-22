const express = require('express');
const cors    = require('cors');
const path    = require('path');
const { getLatest, getHistory, detectAnomalies, getAnomalyHistory } = require('./service');

const app  = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// ── Serve frontend ─────────────────────────────────────────────────────────────
app.use(express.static(path.join(__dirname, '../../frontend')));

// ── REST endpoints ─────────────────────────────────────────────────────────────

app.get('/api/latest', async (req, res) => {
  try { res.json(await getLatest()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

app.get('/api/history', async (req, res) => {
  try { res.json(await getHistory()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

app.get('/api/detect', async (req, res) => {
  try { res.json(await detectAnomalies()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

app.get('/api/anomalies', async (req, res) => {
  try { res.json(await getAnomalyHistory()); }
  catch (e) { res.status(502).json({ error: e.message }); }
});

// ── SSE stream — pushes latest + anomalies every 3 s ──────────────────────────
app.get('/api/stream', (req, res) => {
  res.setHeader('Content-Type',  'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection',    'keep-alive');
  res.flushHeaders();

  const push = async () => {
    try {
      const [latest, detection] = await Promise.all([getLatest(), detectAnomalies()]);
      const payload = JSON.stringify({ latest, anomalies: detection.anomalies });
      res.write(`data: ${payload}\n\n`);
    } catch (e) {
      res.write(`data: ${JSON.stringify({ error: e.message })}\n\n`);
    }
  };

  push();
  const timer = setInterval(push, 3000);
  req.on('close', () => clearInterval(timer));
});

// ── Start ──────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`[BACKEND] Running → http://localhost:${PORT}`);
});