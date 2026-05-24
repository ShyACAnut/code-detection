import axios from 'axios';

const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL,
  timeout: 0,
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

export default api;
