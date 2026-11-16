<template>
  <!-- Verificando sessão salva -->
  <div v-if="isCheckingAuth" class="auth-loading-screen">
    <span class="spinner large" />
    <p>Verificando sua sessão...</p>
  </div>

  <!-- Tela obrigatória de login antes de acessar o sistema -->
  <AuthModal
    v-else-if="!currentUser"
    :is-open="true"
    mode="screen"
    :user="null"
    :notice="authNotice"
    :is-dark-mode="isDarkMode"
    @toggle-theme="toggleTheme"
    @authenticated="handleAuthenticated"
  />

  <div v-else class="app-shell">
    <!-- Sidebar -->
    <ChatSidebar
      :loading="isLoading"
      :is-open="isSidebarOpen"
      :sessions="chatSessions"
      :active-session-id="currentSessionId"
      :saved-count="savedNews.length"
      :sources-count="customSources.length"
      @quick-question="handleQuickQuestion"
      @new-chat="clearChat"
      @select-session="loadSessionDetail"
      @delete-session="handleDeleteSession"
      @open-news-manager="openNewsManager"
    />

    <!-- Mobile Overlay -->
    <transition name="fade">
      <div v-if="isSidebarOpen" class="mobile-overlay" @click="isSidebarOpen = false"></div>
    </transition>

    <!-- Disclaimer Modal -->
    <transition name="fade">
      <div v-if="showDisclaimer" class="modal-overlay" @click.self="closeDisclaimer">
        <div class="modal-content">
          <div class="modal-header">
            <h3>ℹ️ Bem-vindo ao RAG News</h3>
            <button class="close-btn" @click="closeDisclaimer">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
          <div class="modal-body">
            <p>
              O sistema utiliza <strong>OpenRouter</strong> (LLM + Embeddings), <strong>LangGraph</strong> e <strong>PGVector</strong> para responder perguntas baseadas exclusivamente nas notícias indexadas.
            </p>
            <p>
              <strong>Novidades desta versão:</strong><br>
              Crie sua conta ou faça login para salvar notícias, cadastrar fontes RSS/artigos/tópicos personalizados e escolher o escopo do chat (Global, Salvas, Personalizadas ou Acervo Completo).
            </p>
          </div>
          <div class="modal-footer">
            <button class="primary-btn" @click="closeDisclaimer">Entendi</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Profile Modal -->
    <AuthModal
      :is-open="isAuthModalOpen"
      mode="modal"
      :user="currentUser"
      :notice="authNotice"
      :is-dark-mode="isDarkMode"
      @close="isAuthModalOpen = false"
      @authenticated="handleAuthenticated"
      @updated-user="handleUpdatedUser"
      @logout="handleLogout"
    />

    <!-- News & Custom Sources Modal -->
    <NewsManagerModal
      :is-open="isNewsModalOpen"
      :initial-tab="activeNewsTab"
      :current-user="currentUser"
      :saved-news="savedNews"
      :custom-sources="customSources"
      @close="isNewsModalOpen = false"
      @require-auth="handleRequireAuthFromNews"
      @refresh-saved="loadSavedNews"
      @refresh-sources="loadCustomSources"
      @use-scope="handleUseScope"
    />

    <!-- Main chat area -->
    <main class="chat-main">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-info">
          <button class="icon-btn mobile-menu-btn" title="Menu" @click="isSidebarOpen = !isSidebarOpen">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <h1 class="header-title">Chat com Notícias</h1>
        </div>
        <div class="header-actions">
          <button class="pill-btn" title="Central de Notícias & Fontes" @click="openNewsManager('feed')">
            📰 <span class="hide-sm">Acervo</span>
          </button>
          <button class="icon-btn" :title="isDarkMode ? 'Modo Claro' : 'Modo Escuro'" @click="toggleTheme">
            <svg v-if="!isDarkMode" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
          </button>
          <button class="icon-btn" title="Nova conversa" @click="clearChat">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14H6L5 6" />
              <path d="M10 11v6M14 11v6" />
              <path d="M9 6V4h6v2" />
            </svg>
          </button>

          <!-- User profile trigger -->
          <button
            v-if="currentUser"
            class="user-pill-btn"
            title="Gerenciar minha conta"
            @click="openAuthModal('')"
          >
            <img
              v-if="currentUser.picture_url"
              :src="currentUser.picture_url"
              :alt="currentUser.name || currentUser.email"
              class="header-avatar"
              referrerpolicy="no-referrer"
            />
            <span v-else class="header-avatar-fallback">{{ userInitial }}</span>
            <span class="hide-sm">{{ firstName }}</span>
          </button>
          <button v-else class="login-pill-btn" @click="openAuthModal('')">
            Entrar
          </button>
        </div>
      </header>

      <!-- Messages -->
      <section ref="messagesContainer" class="messages-area">
        <!-- Empty state -->
        <div v-if="messages.length === 0" class="empty-state">
          <div class="empty-badge">RAG News · Inteligência Editorial</div>
          <h2 class="empty-title">O que você quer investigar hoje?</h2>
          <p class="empty-sub">
            Pergunte sobre notícias do <strong>Brasil</strong>, <strong>Tecnologia</strong>, <strong>BBC</strong> ou filtre pelo seu <strong>Acervo Pessoal</strong>.
          </p>

          <div class="starter-grid">
            <button
              v-for="card in starterCards"
              :key="card.title"
              type="button"
              class="starter-card"
              @click="handleStarterCard(card)"
            >
              <span class="starter-tag">{{ card.tag }}</span>
              <strong class="starter-title">{{ card.title }}</strong>
              <span class="starter-prompt">{{ card.question }}</span>
            </button>
          </div>
        </div>

        <!-- Message list -->
        <div class="messages-list">
          <ChatMessage
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
            :can-save="Boolean(currentUser)"
            :saved-urls="savedUrls"
            @save-source="handleSaveSourceFromMessage"
          />
        </div>
      </section>

      <!-- Status / Error banners -->
      <transition name="fade">
        <div v-if="statusMessage" class="status-banner">
          {{ statusMessage }}
        </div>
      </transition>

      <transition name="fade">
        <div v-if="errorMessage" class="error-banner">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="error-icon">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {{ errorMessage }}
        </div>
      </transition>

      <!-- Input area -->
      <footer class="input-area">
        <!-- Scope selector -->
        <div class="scope-bar">
          <button
            v-for="option in scopeOptions"
            :key="option.value"
            type="button"
            class="scope-chip"
            :class="{ active: selectedScope === option.value }"
            @click="selectScope(option.value)"
          >
            {{ option.label }}
          </button>

          <select
            v-if="selectedScope === 'custom' && customSources.length > 0"
            v-model="selectedCustomSourceId"
            class="source-filter-select"
          >
            <option :value="null">Todas as fontes personalizadas</option>
            <option v-for="src in customSources" :key="src.id" :value="src.id">
              Somente: {{ src.name }}
            </option>
          </select>
        </div>

        <div class="input-wrapper">
          <textarea
            id="chat-input"
            ref="inputRef"
            v-model="inputText"
            class="chat-input"
            :placeholder="inputPlaceholder"
            rows="1"
            :disabled="isLoading"
            @keydown.enter.prevent="handleEnter"
            @input="autoResize"
          />
          <button
            id="send-btn"
            class="send-btn"
            :disabled="!inputText.trim() || isLoading"
            @click="sendMessage(inputText)"
          >
            <svg v-if="!isLoading" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
            <span v-else class="spinner" />
          </button>
        </div>
        <p class="input-hint">Enter: enviar · Shift+Enter: quebrar linha</p>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import ChatSidebar from "./components/ChatSidebar.vue";
import ChatMessage from "./components/ChatMessage.vue";
import AuthModal from "./components/AuthModal.vue";
import NewsManagerModal from "./components/NewsManagerModal.vue";
import {
  authApi,
  chatApi,
  clearStoredSession,
  getStoredToken,
  getStoredUser,
  newsApi,
  onUnauthorized,
  setStoredSession,
  setStoredUser,
} from "./services/api";

// ─── State ────────────────────────────────────────────────────────────────────

const messages = ref([]);
const inputText = ref("");
const isLoading = ref(false);
const errorMessage = ref("");
const statusMessage = ref("");
const messagesContainer = ref(null);
const inputRef = ref(null);

const isDarkMode = ref(false);
const isSidebarOpen = ref(false);
const showDisclaimer = ref(false);

const currentUser = ref(null);
const isCheckingAuth = ref(Boolean(getStoredToken()));
const isAuthModalOpen = ref(false);
const authNotice = ref("");

const isNewsModalOpen = ref(false);
const activeNewsTab = ref("feed");

const selectedScope = ref("global");
const selectedCustomSourceId = ref(null);
const currentSessionId = ref(null);

const chatSessions = ref([]);
const savedNews = ref([]);
const customSources = ref([]);

const scopeOptions = [
  { value: "global", label: "🌐 Global (Portais)" },
  { value: "saved", label: "🔖 Salvas" },
  { value: "custom", label: "📡 Personalizadas" },
  { value: "personal_all", label: "✨ Acervo Completo" },
];

const starterCards = [
  {
    tag: "🇧🇷 Brasil (PT-BR)",
    title: "Destaques do dia no Brasil",
    question: "Quais são os principais destaques e notícias do Brasil hoje?",
    scope: "global",
  },
  {
    tag: "🤖 Tecnologia & IA",
    title: "Tendências e lançamentos Tech",
    question: "Quais são as principais novidades em Inteligência Artificial e tecnologia?",
    scope: "global",
  },
  {
    tag: "🌍 Mundo & Economia",
    title: "Cenário internacional",
    question: "Quais são os principais acontecimentos internacionais e econômicos hoje?",
    scope: "global",
  },
  {
    tag: "🔖 Meu Acervo",
    title: "Consultar minhas fontes",
    question: "Faça um resumo dos principais pontos das minhas notícias salvas e fontes.",
    scope: "personal_all",
  },
];

const savedUrls = computed(() => savedNews.value.map((n) => n.url));

const userInitial = computed(() => {
  const source = currentUser.value?.name || currentUser.value?.email || "U";
  return source.trim().charAt(0).toUpperCase();
});

const firstName = computed(() => {
  if (currentUser.value?.name) {
    return currentUser.value.name.split(" ")[0];
  }
  return currentUser.value?.email?.split("@")[0] || "Perfil";
});

const inputPlaceholder = computed(() => {
  const map = {
    global: "Pergunte sobre as notícias globais (Brasil, Tech e BBC)...",
    saved: "Pergunte sobre as suas notícias salvas...",
    custom: "Pergunte sobre as suas fontes personalizadas...",
    personal_all: "Pergunte sobre todo o seu acervo pessoal...",
  };
  return map[selectedScope.value] || "Pergunte sobre as notícias...";
});

let msgCounter = 0;
const uid = () => ++msgCounter;

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  const savedTheme = localStorage.getItem("theme");
  if (
    savedTheme === "dark" ||
    (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    isDarkMode.value = true;
    document.documentElement.classList.add("dark");
  }

  if (!localStorage.getItem("disclaimer_seen")) {
    showDisclaimer.value = true;
  }

  onUnauthorized(() => {
    currentUser.value = null;
    isCheckingAuth.value = false;
    chatSessions.value = [];
    savedNews.value = [];
    customSources.value = [];
    currentSessionId.value = null;
    messages.value = [];
    selectedScope.value = "global";
    selectedCustomSourceId.value = null;
    authNotice.value = "Sua sessão expirou. Entre novamente para continuar.";
  });

  if (getStoredToken()) {
    try {
      const me = await authApi.getMe();
      currentUser.value = me;
      setStoredUser(me);
      await loadUserWorkspace();
    } catch {
      clearStoredSession();
      currentUser.value = null;
    } finally {
      isCheckingAuth.value = false;
    }
  } else {
    const cachedUser = getStoredUser();
    if (cachedUser) {
      clearStoredSession();
    }
    isCheckingAuth.value = false;
  }
});

// ─── Auth & User Data ─────────────────────────────────────────────────────────

function openAuthModal(notice = "") {
  authNotice.value = notice;
  isAuthModalOpen.value = true;
  isSidebarOpen.value = false;
}

function handleRequireAuthFromNews(notice) {
  isNewsModalOpen.value = false;
  openAuthModal(notice);
}

async function handleAuthenticated(tokenResponse) {
  setStoredSession(tokenResponse.access_token, tokenResponse.user);
  currentUser.value = tokenResponse.user;
  isAuthModalOpen.value = false;
  authNotice.value = "";
  showStatus("Login realizado com sucesso!");
  await loadUserWorkspace();
}

function handleUpdatedUser(updated) {
  currentUser.value = updated;
  setStoredUser(updated);
}

function handleLogout() {
  clearStoredSession();
  currentUser.value = null;
  chatSessions.value = [];
  savedNews.value = [];
  customSources.value = [];
  currentSessionId.value = null;
  messages.value = [];
  selectedScope.value = "global";
  selectedCustomSourceId.value = null;
  authNotice.value = "Você saiu da sua conta. Entre novamente para continuar.";
}

async function loadUserWorkspace() {
  await Promise.all([loadSessions(), loadSavedNews(), loadCustomSources()]);
}

async function loadSessions() {
  if (!currentUser.value) return;
  try {
    chatSessions.value = await chatApi.getSessions();
  } catch {
    chatSessions.value = [];
  }
}

async function loadSavedNews() {
  if (!currentUser.value) return;
  try {
    savedNews.value = await newsApi.getSavedNews();
  } catch {
    savedNews.value = [];
  }
}

async function loadCustomSources() {
  if (!currentUser.value) return;
  try {
    customSources.value = await newsApi.getCustomSources();
  } catch {
    customSources.value = [];
  }
}

// ─── News Manager & Scope ─────────────────────────────────────────────────────

function openNewsManager(tab = "feed") {
  activeNewsTab.value = tab;
  isNewsModalOpen.value = true;
  isSidebarOpen.value = false;
}

function selectScope(scope) {
  if (scope !== "global" && !currentUser.value) {
    openAuthModal("Entre na sua conta para consultar suas notícias salvas ou personalizadas.");
    return;
  }
  selectedScope.value = scope;
  if (scope !== "custom") {
    selectedCustomSourceId.value = null;
  }
}

function handleUseScope({ scope, customSourceId }) {
  selectedScope.value = scope;
  selectedCustomSourceId.value = customSourceId || null;
  inputRef.value?.focus();
}

async function handleSaveSourceFromMessage(url) {
  if (!currentUser.value) {
    openAuthModal("Entre na sua conta para salvar fontes citadas no chat.");
    return;
  }
  try {
    await newsApi.saveNews({ url, origin: "global_feed" });
    await loadSavedNews();
    showStatus("Notícia salva e indexada na sua conta!");
  } catch (err) {
    showError(err.response?.data?.detail || "Não foi possível salvar a notícia.");
  }
}

// ─── Chat & Sessions ──────────────────────────────────────────────────────────

async function loadSessionDetail(sessionId) {
  isSidebarOpen.value = false;
  errorMessage.value = "";
  try {
    const detail = await chatApi.getSessionDetail(sessionId);
    currentSessionId.value = detail.id;
    selectedScope.value = detail.default_scope || "global";
    messages.value = (detail.messages || []).map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: m.sources || [],
      scope: m.role === "assistant" ? detail.default_scope : undefined,
      isLoading: false,
    }));
    await scrollToBottom();
  } catch (err) {
    showError(err.response?.data?.detail || "Erro ao carregar histórico da conversa.");
  }
}

async function handleDeleteSession(sessionId) {
  try {
    await chatApi.deleteSession(sessionId);
    chatSessions.value = chatSessions.value.filter((s) => s.id !== sessionId);
    if (currentSessionId.value === sessionId) {
      clearChat();
    }
  } catch (err) {
    showError(err.response?.data?.detail || "Erro ao excluir conversa.");
  }
}

function handleQuickQuestion(text) {
  isSidebarOpen.value = false;
  sendMessage(text);
}

function handleStarterCard(card) {
  selectedScope.value = card.scope || "global";
  if (selectedScope.value !== "custom") {
    selectedCustomSourceId.value = null;
  }
  sendMessage(card.question);
}

async function sendMessage(text) {
  const question = (typeof text === "string" ? text : inputText.value).trim();
  if (!question || isLoading.value) return;

  if (selectedScope.value !== "global" && !currentUser.value) {
    openAuthModal("Entre na sua conta para consultar este escopo.");
    return;
  }

  errorMessage.value = "";
  inputText.value = "";
  resetTextareaHeight();

  messages.value.push({ id: uid(), role: "user", content: question });

  const loadingMsg = { id: uid(), role: "assistant", content: "", isLoading: true };
  messages.value.push(loadingMsg);
  await scrollToBottom();

  isLoading.value = true;

  try {
    const data = await chatApi.ask({
      question,
      scope: selectedScope.value,
      session_id: currentSessionId.value,
      custom_source_id:
        selectedScope.value === "custom" ? selectedCustomSourceId.value : null,
    });

    if (data.session_id) {
      currentSessionId.value = data.session_id;
    }

    const idx = messages.value.findIndex((m) => m.id === loadingMsg.id);
    if (idx !== -1) {
      messages.value[idx] = {
        id: loadingMsg.id,
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        scope: data.scope || selectedScope.value,
        isLoading: false,
      };
    }

    if (currentUser.value) {
      await loadSessions();
    }
  } catch (err) {
    messages.value = messages.value.filter((m) => m.id !== loadingMsg.id);
    showError(
      "Erro ao obter resposta: " +
        (err.response?.data?.detail || err.message || "Tente novamente.")
    );
  } finally {
    isLoading.value = false;
    await scrollToBottom();
    inputRef.value?.focus();
  }
}

function clearChat() {
  messages.value = [];
  currentSessionId.value = null;
  errorMessage.value = "";
  isSidebarOpen.value = false;
}

function closeDisclaimer() {
  showDisclaimer.value = false;
  localStorage.setItem("disclaimer_seen", "true");
}

function toggleTheme() {
  isDarkMode.value = !isDarkMode.value;
  if (isDarkMode.value) {
    document.documentElement.classList.add("dark");
    localStorage.setItem("theme", "dark");
  } else {
    document.documentElement.classList.remove("dark");
    localStorage.setItem("theme", "light");
  }
}

function handleEnter(event) {
  if (event.shiftKey) return;
  sendMessage(inputText.value);
}

function showStatus(msg) {
  statusMessage.value = msg;
  setTimeout(() => {
    if (statusMessage.value === msg) statusMessage.value = "";
  }, 4000);
}

function showError(msg) {
  errorMessage.value = msg;
  setTimeout(() => {
    if (errorMessage.value === msg) errorMessage.value = "";
  }, 5000);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function scrollToBottom() {
  await nextTick();
  const el = messagesContainer.value;
  if (el) el.scrollTop = el.scrollHeight;
}

function autoResize(event) {
  const ta = event.target;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}

function resetTextareaHeight() {
  if (inputRef.value) inputRef.value.style.height = "auto";
}
</script>

<style scoped>
.auth-loading-screen {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.9rem;
  background: var(--color-bg-primary);
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.spinner.large {
  width: 28px;
  height: 28px;
  border-width: 3px;
  border-color: var(--color-border);
  border-top-color: var(--color-accent);
}

/* ── Shell ───────────────────────────────────────────────────────────────── */
.app-shell {
  display: flex;
  height: 100dvh;
  overflow: hidden;
  background: var(--color-bg-primary);
  position: relative;
}

.mobile-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  z-index: 40;
}

/* ── Modal ───────────────────────────────────────────────────────────────── */
.modal-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(3px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.modal-content {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-text-primary);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  display: flex;
}

.close-btn:hover {
  color: var(--color-text-primary);
}

.modal-body {
  padding: 1.5rem;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.modal-body p {
  margin-top: 0;
  margin-bottom: 1rem;
}

.modal-body p:last-child {
  margin-bottom: 0;
}

.modal-body strong {
  color: var(--color-text-primary);
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  background: var(--color-bg-secondary);
}

.primary-btn {
  background: var(--color-accent);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.primary-btn:hover {
  opacity: 0.9;
}

/* ── Main ────────────────────────────────────────────────────────────────── */
.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  overflow: hidden;
}

/* ── Header ──────────────────────────────────────────────────────────────── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
  gap: 0.75rem;
}
.header-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.icon-btn.mobile-menu-btn {
  display: none;
}
.header-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}
.icon-btn:hover {
  border-color: var(--color-text-muted);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
}
.icon-btn svg {
  width: 16px;
  height: 16px;
}

.pill-btn,
.user-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  height: 34px;
  padding: 0 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
}
.pill-btn:hover,
.user-pill-btn:hover {
  border-color: var(--color-accent);
}
.login-pill-btn {
  height: 34px;
  padding: 0 0.85rem;
  border-radius: 8px;
  border: none;
  background: var(--color-accent);
  color: white;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}
.header-avatar,
.header-avatar-fallback {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: cover;
}
.header-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-accent);
  color: white;
  font-size: 0.72rem;
  font-weight: 700;
}

/* ── Messages ─────────────────────────────────────────────────────────────── */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  scroll-behavior: smooth;
}
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  width: 100%;
  align-items: center;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  gap: 0.75rem;
  padding: 2rem 1rem;
  color: var(--color-text-secondary);
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
}
.empty-badge {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-accent-light);
  background: var(--color-accent-soft);
  border: 1px solid rgba(59, 130, 246, 0.25);
  padding: 0.3rem 0.75rem;
  border-radius: 99px;
}
.empty-title {
  margin: 0.2rem 0 0;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--color-text-primary);
}
.empty-sub {
  margin: 0;
  font-size: 0.88rem;
  max-width: 480px;
  line-height: 1.6;
}
.starter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  width: 100%;
  margin-top: 1rem;
}
.starter-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  gap: 0.35rem;
  padding: 0.95rem 1rem;
  border-radius: 12px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  box-shadow: var(--color-shadow-sm);
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.starter-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-accent);
  box-shadow: var(--color-shadow-md);
}
.starter-tag {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-accent-light);
}
.starter-title {
  font-size: 0.88rem;
  color: var(--color-text-primary);
}
.starter-prompt {
  font-size: 0.76rem;
  line-height: 1.45;
  color: var(--color-text-muted);
}

/* ── Banners ──────────────────────────────────────────────────────────────── */
.status-banner {
  margin: 0 1.5rem 0.5rem;
  padding: 0.55rem 1rem;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  border-radius: 8px;
  color: #4ade80;
  font-size: 0.82rem;
  flex-shrink: 0;
}
.error-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 1.5rem 0.5rem;
  padding: 0.6rem 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #f87171;
  font-size: 0.82rem;
  flex-shrink: 0;
}
.error-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── Input area ───────────────────────────────────────────────────────────── */
.input-area {
  padding: 0.75rem 1.5rem 1.15rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}
.scope-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.65rem;
}
.scope-chip {
  padding: 0.32rem 0.7rem;
  border-radius: 99px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  font-size: 0.76rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}
.scope-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-text-primary);
}
.scope-chip.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
  font-weight: 600;
}
.source-filter-select {
  padding: 0.3rem 0.6rem;
  border-radius: 99px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.76rem;
  outline: none;
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 0.5rem 0.5rem 0.5rem 1rem;
  transition: border-color 0.2s;
}
.input-wrapper:focus-within {
  border-color: var(--color-text-muted);
}
.chat-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  color: var(--color-text-primary);
  font-size: 0.9rem;
  font-family: "Inter", sans-serif;
  line-height: 1.5;
  max-height: 140px;
  overflow-y: auto;
}
.chat-input::placeholder {
  color: var(--color-text-muted);
}
.chat-input:disabled {
  opacity: 0.6;
}
.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  align-self: flex-end;
  background: var(--color-accent);
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.2s ease;
}
.send-btn:hover:not(:disabled) {
  opacity: 0.9;
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.send-btn svg {
  width: 18px;
  height: 18px;
}
.input-hint {
  margin: 0.4rem 0 0;
  font-size: 0.68rem;
  color: var(--color-text-muted);
  text-align: right;
}

/* Spinner */
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── Responsive ───────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .starter-grid {
    grid-template-columns: 1fr;
  }
  .icon-btn.mobile-menu-btn {
    display: flex;
  }
  .hide-sm {
    display: none;
  }
  .chat-header {
    padding: 0.8rem 1rem;
  }
  .messages-area {
    padding: 1rem 0.5rem;
  }
  .input-area {
    padding: 0.75rem;
  }
}
</style>
