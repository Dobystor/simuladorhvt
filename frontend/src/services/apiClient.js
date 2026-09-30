import axios from 'axios';
import { useAppStore } from '../store/appStore';

const apiClient = axios.create({
  baseURL: '/api',
});

// Attach the session token to every request.
apiClient.interceptors.request.use((config) => {
  const session = useAppStore.getState().session;
  if (session?.token) {
    config.headers.Authorization = `Bearer ${session.token}`;
  }
  return config;
});

// On 401, clear the session and redirect to login.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAppStore.getState().clearSession();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
