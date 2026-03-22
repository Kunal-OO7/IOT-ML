const axios = require('axios');

const ML_URL = 'http://localhost:5000';

// Shared axios instance with timeout
const http = axios.create({ baseURL: ML_URL, timeout: 5000 });

const getLatest = async () => {
  const { data } = await http.get('/latest');
  return data;
};

const getHistory = async () => {
  const { data } = await http.get('/history');
  return data;
};

const detectAnomalies = async () => {
  const { data } = await http.get('/detect');
  return data;
};

const getAnomalyHistory = async () => {
  const { data } = await http.get('/anomaly-history');
  return data;
};

module.exports = { getLatest, getHistory, detectAnomalies, getAnomalyHistory };