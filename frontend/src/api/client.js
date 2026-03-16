import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Make sure this matches fastAPI 

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analyzeBBox = async (bbox) => {
  const response = await apiClient.post('/analyze/bbox', bbox);
  return response.data;
};

export const analyzePolygon = async (polygonData) => {
  const response = await apiClient.post('/analyze/polygon', polygonData);
  return response.data;
};

export const generateReport = async (stats, extraContext = '') => {
  const response = await apiClient.post('/report', {
    stats: stats,
    extra_context: extraContext
  });
  return response.data;
};

export default apiClient;

export const generateTextReport = async (blockId) => {
  return await apiClient.post('/report', { block_id: blockId });
};

export const generatePdfReport = async (blockId) => {
  return await apiClient.post('/report/pdf', { block_id: blockId }, { responseType: 'blob' });
};
