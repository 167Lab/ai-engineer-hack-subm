import axios from 'axios';

// Используем относительный путь, чтобы сохранить одну origin и сессионные cookie (для Airflow proxy)
const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach Authorization header if token present
apiClient.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers = config.headers || {};
      (config.headers as any)['Authorization'] = `Bearer ${token}`;
    }
  } catch (_) {}
  return config;
});

export const analyzeDataSource = async (data: any) => {
  const response = await apiClient.post('/analyze', data);
  return response.data;
};

export const generatePipeline = async (data: { session_id: string; user_choices: any }) => {
  const response = await apiClient.post('/generate_pipeline', data);
  return response.data;
};

export const generateReport = async (data: { session_id: string }) => {
  const response = await apiClient.post('/generate_report', data);
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

export const login = async (credentials: { username: string; password: string }) => {
  const response = await apiClient.post('/auth/login', credentials);
  return response.data;
};

export type FileNode = {
  title: string;
  key: string; // full path
  isLeaf?: boolean;
  children?: FileNode[];
};

export const listFiles = async (params: { path: string; depth?: number }) => {
  const { path, depth = 3 } = params;
  const response = await apiClient.get('/list_files', { params: { path, depth } });
  return response.data as { tree: FileNode };
};

export const previewFile = async (params: { path: string; type: 'csv'|'json'|'xml'; rows?: number }) => {
  const { path, type, rows = 50 } = params;
  const response = await apiClient.get('/preview', { params: { path, type, rows } });
  return response.data as { columns: string[]; rows: any[] };
};

export const bootstrapAirflowSession = async (airflowUrl?: string) => {
  const response = await apiClient.post('/airflow/bootstrap-session', {
    airflow_url: airflowUrl || 'http://localhost:8080',
  });
  return response.data as { status: string; airflow_ui_url?: string };
};

export const logout = async () => {
  try {
    await apiClient.post('/auth/logout');
  } catch (_) {}
}
