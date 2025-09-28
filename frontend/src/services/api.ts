import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analyzeDataSource = async (data: any) => {
  const response = await apiClient.post('/analyze', data);
  return response.data;
};

export const generateDag = async (data: any) => {
  const response = await apiClient.post('/generate_dag', data);
  return response.data;
};

export const getRecommendations = async (sourceId: string) => {
  const response = await apiClient.get(`/recommendations?source_id=${sourceId}`);
  return response.data;
};

export const deployDag = async (data: any) => {
  const response = await apiClient.post('/deploy_dag', data);
  return response.data;
};
