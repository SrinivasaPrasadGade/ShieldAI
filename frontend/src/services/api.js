// frontend/src/services/api.js
import axios from 'axios';
import { auth } from './firebase';
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use(async (config) => {
  if (auth.currentUser) {
    try {
      const token = await auth.currentUser.getIdToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (e) {
      console.error("Error getting auth token", e);
    }
  }
  return config;
}, (error) => Promise.reject(error));

client.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  }
);

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

  markAlertRead: async (alertId) => {
    const res = await client.post(`/api/scam/alerts/${alertId}/read`);
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

  getRecomputeStatus: async () => {
    const res = await client.get('/api/graph/recompute-status');
    return res.data;
  },

  startEvidencePackage: async (clusterId, officerMetadata = { officer_name: "System", badge_number: "000", department: "HQ" }) => {
    const res = await client.post(`/api/graph/evidence-package/${clusterId}`, officerMetadata);
    return res.data;
  },

  verifyEvidencePackage: async (evidencePackage) => {
    const res = await client.post(`/api/graph/evidence-package/verify`, { evidence_package: evidencePackage });
    return res.data;
  },

  getEvidencePackageResult: async (taskId) => {
    const res = await client.get(`/api/graph/evidence-package/result/${taskId}`);
    return res.data;
  },

  getGraphStats: async () => {
    const res = await client.get('/api/graph/stats');
    return res.data;
  },

  // Geospatial Intelligence
  getGeoIncidents: async (type = '', days = 7, state = '') => {
    const params = { days };
    if (type) params.type = type;
    if (state) params.state = state;
    const res = await client.get('/api/geo/incidents', { params });
    return res.data;
  },

  getGeoHeatmap: async (type = '') => {
    const params = {};
    if (type) params.type = type;
    const res = await client.get('/api/geo/heatmap', { params });
    return res.data;
  },

  // Citizen Shield
  sendChatMessage: async (message, sessionId, language = 'en') => {
    const res = await client.post('/api/citizen/chat', { message, session_id: sessionId, language });
    return res.data;
  },

  submitReport: async (description, phoneNumber = '', location = '', contactEmail = '', source = 'web') => {
    const res = await client.post('/api/citizen/report', {
      description,
      phone_number: phoneNumber,
      location,
      contact_email: contactEmail,
      source,
    });
    return res.data;
  },
};
