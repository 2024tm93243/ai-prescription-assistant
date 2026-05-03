/**
 * API Service for Prescription Reader
 * Handles all communication with the backend API Gateway
 */

import axios from 'axios';

// API base URL - uses proxy in development
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 150000, // 2.5 minutes for OCR processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercept errors and provide user-friendly timeout messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      error.userMessage = 'The request timed out. The server is taking too long to respond. Please try again.';
    } else if (error.response?.status === 504) {
      error.userMessage = error.response.data?.detail || 'Gateway timeout. Please try again in a moment.';
    } else if (error.response?.status === 503) {
      error.userMessage = 'Service is temporarily unavailable. Please try again shortly.';
    } else if (!error.response) {
      error.userMessage = 'Cannot reach the server. Please check your connection and try again.';
    }
    return Promise.reject(error);
  }
);

/**
 * Upload a prescription image for processing
 * @param {File} file - The prescription image file
 * @returns {Promise} - Upload result with medications
 */
export const uploadPrescription = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/upload-prescription', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Get educational information about a drug
 * @param {string} drugName - Name of the drug
 * @returns {Promise} - Drug information with uses, side effects, warnings
 */
export const getDrugInfo = async (drugName) => {
  const response = await api.get(`/api/drug-info/${encodeURIComponent(drugName)}`);
  return response.data;
};

/**
 * Confirm a low-confidence drug name
 * @param {string} prescriptionId - Prescription session ID
 * @param {string} drugId - Drug ID to confirm
 * @param {string} confirmedName - User-confirmed drug name
 * @returns {Promise} - Confirmation result
 */
export const confirmDrug = async (prescriptionId, drugId, confirmedName) => {
  const response = await api.post('/api/confirm-drug', {
    prescription_id: prescriptionId,
    drug_id: drugId,
    confirmed_name: confirmedName,
  });

  return response.data;
};

/**
 * Get prescription data by ID
 * @param {string} prescriptionId - Prescription session ID
 * @returns {Promise} - Prescription data
 */
export const getPrescription = async (prescriptionId) => {
  const response = await api.get(`/api/prescription/${prescriptionId}`);
  return response.data;
};

/**
 * Delete prescription data
 * @param {string} prescriptionId - Prescription session ID
 * @returns {Promise} - Deletion result
 */
export const deletePrescription = async (prescriptionId) => {
  const response = await api.delete(`/api/prescription/${prescriptionId}`);
  return response.data;
};

/**
 * Get the educational disclaimer
 * @returns {Promise} - Disclaimer text
 */
export const getDisclaimer = async () => {
  const response = await api.get('/api/disclaimer');
  return response.data;
};

/**
 * Get API information
 * @returns {Promise} - API info and capabilities
 */
export const getApiInfo = async () => {
  const response = await api.get('/api/info');
  return response.data;
};

/**
 * Check services health
 * @returns {Promise} - Health status of all services
 */
export const checkServicesHealth = async () => {
  const response = await api.get('/health/services');
  return response.data;
};

export default api;
