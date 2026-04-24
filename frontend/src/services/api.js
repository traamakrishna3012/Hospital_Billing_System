import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const getApiBaseUrl = () => {
  // Always use the same origin in production to avoid CORS and stale URL issues
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000/api/v1';
  }
  return `${window.location.origin}/api/v1`;
};

const base = getApiBaseUrl();


const api = axios.create({
  baseURL: base,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // Crucial for sending HttpOnly cookies
});

// Handle 401 — auto refresh or logout
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const authStore = useAuthStore.getState();

    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Call refresh endpoint — browser sends refresh_token cookie automatically
        await axios.post(`${api.defaults.baseURL}/auth/refresh`, {}, { withCredentials: true });
        // Retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        authStore.logout();
        // Fail silently on refresh failure to avoid console noise
        return new Promise(() => {}); 
      }
    }
    return Promise.reject(error);
  }
);



// ── Auth API ─────────────────────────────────────────────────

export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: (data) => api.post('/auth/logout', data),
  getMe: () => api.get('/auth/me'),
};

// ── Patient API ──────────────────────────────────────────────

export const patientAPI = {
  list: (params) => api.get('/patients', { params }),
  get: (id) => api.get(`/patients/${id}`),
  create: (data) => api.post('/patients', data),
  update: (id, data) => api.put(`/patients/${id}`, data),
  delete: (id) => api.delete(`/patients/${id}`),
};

// ── Doctor API ───────────────────────────────────────────────

export const doctorAPI = {
  list: (params) => api.get('/doctors', { params }),
  get: (id) => api.get(`/doctors/${id}`),
  create: (data) => api.post('/doctors', data),
  update: (id, data) => api.put(`/doctors/${id}`, data),
  delete: (id) => api.delete(`/doctors/${id}`),
};

// ── Test API ─────────────────────────────────────────────────

export const testAPI = {
  listCategories: () => api.get('/tests/categories'),
  createCategory: (data) => api.post('/tests/categories', data),
  updateCategory: (id, data) => api.put(`/tests/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/tests/categories/${id}`),
  list: (params) => api.get('/tests', { params }),
  get: (id) => api.get(`/tests/${id}`),
  create: (data) => api.post('/tests', data),
  update: (id, data) => api.put(`/tests/${id}`, data),
  delete: (id) => api.delete(`/tests/${id}`),
  bulkImport: (formData) => api.post('/tests/bulk-upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

// ── Billing API ──────────────────────────────────────────────

export const billAPI = {
  list: (params) => api.get('/bills', { params }),
  get: (id) => api.get(`/bills/${id}`),
  create: (data) => api.post('/bills', data),
  update: (id, data) => api.put(`/bills/${id}`, data),
  delete: (id) => api.delete(`/bills/${id}`),
  downloadPDF: (id) => api.get(`/bills/${id}/pdf`, { responseType: 'arraybuffer' }),
  sendEmail: (id) => api.post(`/bills/${id}/send-email`),
};

// ── Clinic API ───────────────────────────────────────────────

export const clinicAPI = {
  getProfile: () => api.get('/clinic'),
  updateProfile: (data) => api.put('/clinic', data),
  uploadLogo: (formData) => api.post('/clinic/logo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getSubscription: () => api.get('/clinic/subscription'),
};

// ── Dashboard API ────────────────────────────────────────────

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
  getChartData: (params) => api.get('/dashboard/chart-data', { params }),
  getRecent: (params) => api.get('/dashboard/recent', { params }),
};

// ── User/Staff API ───────────────────────────────────────────

export const userAPI = {
  list: (params) => api.get('/users', { params }),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
};

// ── Reports API ──────────────────────────────────────────────

export const reportAPI = {
  exportCSV: (params) => api.get('/reports/export/csv', { params, responseType: 'blob' }),
};

// ── Super Admin API ──────────────────────────────────────────

export const superadminAPI = {
  getStats: () => api.get('/superadmin/stats'),
  listTenants: (params) => api.get('/superadmin/tenants', { params }),
  getTenant: (id) => api.get(`/superadmin/tenants/${id}`),
  updateTenant: (id, data) => api.patch(`/superadmin/tenants/${id}`, data),
  deactivateTenant: (id) => api.delete(`/superadmin/tenants/${id}`),
  listAllUsers: (params) => api.get('/superadmin/users', { params }),
};

export default api;
