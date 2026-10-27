import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from 'axios'
import { getAccessToken, initAuth } from './composables/useAuth'

axios.defaults.baseURL = import.meta.env.VITE_API_URL || '';

// Envia o token do usuário logado em todas as chamadas à API.
// Sem login, as requisições seguem anônimas como antes.
axios.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

initAuth();

createApp(App).mount('#app')
