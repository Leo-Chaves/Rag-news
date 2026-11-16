import axios from "axios";

const TOKEN_STORAGE_KEY = "rag_news_token";
const USER_STORAGE_KEY = "rag_news_user";

let unauthorizedHandler = null;

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || "";
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setStoredSession(token, user) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
  if (user) {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  }
}

export function clearStoredSession() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);
}

export function onUnauthorized(callback) {
  unauthorizedHandler = callback;
}

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const requestUrl = error.config?.url || "";
    const isAuthAttempt =
      requestUrl.includes("/auth/login") || requestUrl.includes("/auth/register");
    if (status === 401 && !isAuthAttempt && getStoredToken()) {
      clearStoredSession();
      if (typeof unauthorizedHandler === "function") {
        unauthorizedHandler();
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  async register({ name, email, password }) {
    const { data } = await apiClient.post("/auth/register", {
      name: name || null,
      email,
      password,
    });
    return data;
  },
  async login({ email, password }) {
    const { data } = await apiClient.post("/auth/login", {
      email,
      password,
    });
    return data;
  },
  async getMe() {
    const { data } = await apiClient.get("/auth/me");
    return data;
  },
};

export const usersApi = {
  async getProfile() {
    const { data } = await apiClient.get("/users/me");
    return data;
  },
  async updateProfile(payload) {
    const { data } = await apiClient.patch("/users/me", payload);
    return data;
  },
};

export const newsApi = {
  async getGlobalFeed(limit = 60) {
    const { data } = await apiClient.get("/news/feed", { params: { limit } });
    return data;
  },
  async ingestGlobalFeed() {
    const { data } = await apiClient.post("/news/ingest");
    return data;
  },
  async getSavedNews() {
    const { data } = await apiClient.get("/news/saved");
    return data;
  },
  async saveNews(payload) {
    const { data } = await apiClient.post("/news/saved", payload);
    return data;
  },
  async deleteSavedNews(newsId) {
    await apiClient.delete(`/news/saved/${newsId}`);
  },
  async getCustomSources() {
    const { data } = await apiClient.get("/news/sources");
    return data;
  },
  async createCustomSource(payload) {
    const { data } = await apiClient.post("/news/sources", payload);
    return data;
  },
  async syncCustomSource(sourceId) {
    const { data } = await apiClient.post(`/news/sources/${sourceId}/sync`);
    return data;
  },
  async deleteCustomSource(sourceId) {
    await apiClient.delete(`/news/sources/${sourceId}`);
  },
};

export const chatApi = {
  async ask({ question, scope = "global", session_id = null, custom_source_id = null, top_k = 5 }) {
    const body = { question, scope, top_k };
    if (session_id) body.session_id = session_id;
    if (custom_source_id) body.custom_source_id = custom_source_id;
    const { data } = await apiClient.post("/chat", body);
    return data;
  },
  async getSessions() {
    const { data } = await apiClient.get("/chat/sessions");
    return data;
  },
  async getSessionDetail(sessionId) {
    const { data } = await apiClient.get(`/chat/sessions/${sessionId}`);
    return data;
  },
  async deleteSession(sessionId) {
    await apiClient.delete(`/chat/sessions/${sessionId}`);
  },
};

