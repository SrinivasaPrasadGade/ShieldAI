// frontend/src/services/api.js
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Scam Detection
  analyzeScamText: async (text, sourcePhone = '', language = 'en') => {
    const res = await client.post('/api/scam/analyze', { text, source_phone: sourcePhone, language });
    return res.data;
  },
  
  getAlerts: async (limit = 20, severity = '') => {
    const params = {};
    if (severity) params.severity = severity;
    const res = await client.get('/api/scam/alerts', { params });
    return res.data;
  },

  // Currency Verification
  verifyCurrency: async (imageFile, denomination = null) => {
    const formData = new FormData();
    formData.append('image', imageFile);
    if (denomination) {
      formData.append('denomination', denomination);
    }
    const res = await client.post('/api/currency/verify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  getTaskResult: async (taskId) => {
    const res = await client.get(`/api/currency/result/${taskId}`);
    return res.data;
  },

  // Fraud Network Graph
  getNetwork: async (clusterId = null, limit = 100) => {
    const params = { limit };
    if (clusterId !== null) params.cluster_id = clusterId;
    const res = await client.get('/api/graph/network', { params });
    return res.data;
  },

  getNodeDetails: async (entityId) => {
    const res = await client.get(`/api/graph/node/${entityId}`);
    return res.data;
  },

  getClusters: async () => {
    const res = await client.get('/api/graph/clusters');
    return res.data;
  },

  getGraphStats: async () => {
    const res = await client.get('/api/graph/stats');
    return res.data;
  },

  // Citizen Shield
  sendChatMessage: async (message, sessionId, language = 'en') => {
    const res = await client.post('/api/citizen/chat', { message, session_id: sessionId, language });
    return res.data;
  },

  submitReport: async (description, phoneNumber = '', location = '', contactEmail = '') => {
    const res = await client.post('/api/citizen/report', {
      description,
      phone_number: phoneNumber,
      location,
      contact_email: contactEmail,
    });
    return res.data;
  },
};
