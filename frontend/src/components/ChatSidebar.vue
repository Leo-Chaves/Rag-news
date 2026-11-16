<template>
  <!-- Sidebar -->
  <aside class="sidebar" :class="{ 'is-open': isOpen }">
    <!-- Logo / Brand -->
    <div class="sidebar-brand">
      <div class="brand-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v2" />
          <path d="M2 20h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H2" />
          <path d="M6 10h8M6 14h8M6 18h4" />
        </svg>
      </div>
      <div class="brand-text">
        <span class="brand-title">RAG News</span>
        <span class="brand-sub">OpenRouter · PGVector</span>
      </div>
    </div>

    <!-- Nova Conversa -->
    <button class="new-chat-btn" :disabled="props.loading" @click="$emit('new-chat')">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
        <line x1="12" y1="5" x2="12" y2="19" />
        <line x1="5" y1="12" x2="19" y2="12" />
      </svg>
      <span>Nova Conversa</span>
    </button>

    <!-- Biblioteca & Fontes -->
    <div class="sidebar-section">
      <p class="sidebar-section-title">Biblioteca & Fontes</p>
      <div class="nav-list">
        <button class="nav-item-btn" @click="$emit('open-news-manager', 'feed')">
          <span>🌐 Explorar Feed BBC</span>
        </button>
        <button class="nav-item-btn" @click="$emit('open-news-manager', 'saved')">
          <span>🔖 Notícias Salvas</span>
          <span v-if="currentUser" class="count-pill">{{ savedCount }}</span>
        </button>
        <button class="nav-item-btn" @click="$emit('open-news-manager', 'sources')">
          <span>📡 Fontes Personalizadas</span>
          <span v-if="currentUser" class="count-pill">{{ sourcesCount }}</span>
        </button>
      </div>
    </div>

    <!-- Histórico de Sessões -->
    <div class="sidebar-section">
      <p class="sidebar-section-title">Histórico de Conversas</p>

      <div v-if="!currentUser" class="auth-hint-card">
        <p>Entre com o Google para salvar seu histórico de perguntas e consultar notícias privadas.</p>
        <button class="auth-hint-btn" @click="$emit('open-auth')">Entrar com Google</button>
      </div>

      <div v-else-if="sessions.length === 0" class="empty-sessions">
        Nenhuma conversa salva ainda.
      </div>

      <div v-else class="sessions-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === activeSessionId }"
          @click="$emit('select-session', session.id)"
        >
          <div class="session-info">
            <span class="session-title">{{ session.title }}</span>
            <span class="session-scope">{{ formatScope(session.default_scope) }}</span>
          </div>
          <button
            class="session-delete-btn"
            title="Excluir conversa"
            @click.stop="$emit('delete-session', session.id)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14H6L5 6" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Quick Questions -->
    <div class="sidebar-section">
      <p class="sidebar-section-title">Perguntas Rápidas</p>
      <div class="quick-questions">
        <button
          v-for="q in quickQuestions"
          :key="q.id"
          class="quick-btn"
          :disabled="props.loading"
          @click="$emit('quick-question', q.text)"
        >
          <span class="quick-btn-text">{{ q.text }}</span>
        </button>
      </div>
    </div>

    <!-- Ingest BBC Feeds -->
    <div class="sidebar-section sidebar-footer">
      <p class="sidebar-section-title">Feeds BBC (Global)</p>

      <div class="feeds-list">
        <div v-for="feed in bbcFeeds" :key="feed.label" class="feed-item">
          <span class="feed-dot" />
          <span>{{ feed.label }}</span>
        </div>
      </div>

      <button
        class="ingest-btn"
        :disabled="props.loading || isIngesting"
        @click="handleIngest"
      >
        <span v-if="isIngesting" class="spinner" />
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
          <polyline points="1 4 1 10 7 10" />
          <path d="M3.51 15a9 9 0 1 0 .49-3.08" />
        </svg>
        <span>{{ isIngesting ? "Carregando feeds..." : "Atualizar Notícias" }}</span>
      </button>

      <p v-if="ingestMessage" class="ingest-message" :class="ingestSuccess ? 'success' : 'error'">
        {{ ingestMessage }}
      </p>
    </div>
  </aside>
</template>

<script setup>
import { ref } from "vue";
import { newsApi } from "../services/api";

const props = defineProps({
  loading: { type: Boolean, default: false },
  isOpen: { type: Boolean, default: false },
  currentUser: { type: Object, default: null },
  sessions: { type: Array, default: () => [] },
  activeSessionId: { type: String, default: null },
  savedCount: { type: Number, default: 0 },
  sourcesCount: { type: Number, default: 0 },
});

defineEmits([
  "quick-question",
  "new-chat",
  "select-session",
  "delete-session",
  "open-news-manager",
  "open-auth",
]);

const quickQuestions = [
  { id: 1, text: "O que aconteceu no recente ataque de drones a Moscou?" },
  { id: 2, text: "Quais são os planos de Donald Trump para o arco do triunfo?" },
  { id: 3, text: "O que Earl Spencer falou sobre a Princesa Diana na sua entrevista à BBC?" },
  { id: 4, text: "O que o Chanceler alemão Merz comentou sobre os resultados das eleições?" },
  { id: 5, text: "O que aconteceu no futebol hoje?" },
];

const bbcFeeds = [
  { label: "BBC News — Geral" },
  { label: "BBC News — Mundo" },
  { label: "BBC News — Tecnologia" },
  { label: "BBC News — Negócios" },
  { label: "BBC News — Ciência & Ambiente" },
];

const isIngesting = ref(false);
const ingestMessage = ref("");
const ingestSuccess = ref(false);

function formatScope(scope) {
  const map = {
    global: "Global",
    saved: "Salvas",
    custom: "Personalizadas",
    personal_all: "Acervo Pessoal",
  };
  return map[scope] || scope;
}

async function handleIngest() {
  isIngesting.value = true;
  ingestMessage.value = "";

  try {
    const data = await newsApi.ingestGlobalFeed();
    ingestSuccess.value = true;
    if (data.chunks_stored === 0 && data.skipped > 0) {
      ingestMessage.value = `✅ Notícias já atualizadas! (${data.skipped} artigos já existiam)`;
    } else if (data.skipped > 0) {
      ingestMessage.value = `✅ ${data.chunks_stored} chunks de ${data.articles_processed} novos artigos salvos! (${data.skipped} já existiam)`;
    } else {
      ingestMessage.value = `✅ ${data.chunks_stored} chunks de ${data.articles_processed} artigos salvos!`;
    }
  } catch (err) {
    ingestSuccess.value = false;
    ingestMessage.value =
      "❌ " + (err.response?.data?.detail || "Erro ao ingerir feeds.");
  } finally {
    isIngesting.value = false;
  }
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: 290px;
  min-width: 290px;
  height: 100%;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  padding: 1.25rem 1rem;
  gap: 1.15rem;
  overflow-y: auto;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 50;
}

/* Brand */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}
.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  background: var(--color-accent);
  border-radius: 8px;
  color: white;
}
.brand-icon svg {
  width: 19px;
  height: 19px;
}
.brand-text {
  display: flex;
  flex-direction: column;
}
.brand-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}
.brand-sub {
  font-size: 0.7rem;
  color: var(--color-accent-light);
  font-weight: 500;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text-primary);
  font-size: 0.82rem;
  font-weight: 600;
  font-family: "Inter", sans-serif;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.new-chat-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
}
.new-chat-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Sections */
.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.sidebar-section-title {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin: 0;
}

/* Library nav */
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.nav-item-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.5rem 0.7rem;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text-primary);
  font-size: 0.8rem;
  font-family: "Inter", sans-serif;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.nav-item-btn:hover {
  border-color: var(--color-accent);
}
.count-pill {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.1rem 0.45rem;
  border-radius: 99px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

/* Sessions */
.auth-hint-card {
  padding: 0.7rem;
  border-radius: 8px;
  border: 1px dashed var(--color-border);
  background: var(--color-bg-primary);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.auth-hint-card p {
  margin: 0;
  font-size: 0.74rem;
  line-height: 1.4;
  color: var(--color-text-secondary);
}
.auth-hint-btn {
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.42rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}
.empty-sessions {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  padding: 0.25rem 0;
}
.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  max-height: 185px;
  overflow-y: auto;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  padding: 0.45rem 0.6rem;
  border-radius: 8px;
  border: 1px solid transparent;
  background: var(--color-bg-primary);
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.session-item:hover {
  border-color: var(--color-border);
}
.session-item.active {
  border-color: var(--color-accent);
  background: var(--color-bg-card);
}
.session-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.1rem;
}
.session-title {
  font-size: 0.78rem;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-scope {
  font-size: 0.65rem;
  color: var(--color-text-muted);
}
.session-delete-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0.2rem;
  display: flex;
  flex-shrink: 0;
}
.session-delete-btn:hover {
  color: #f87171;
}
.session-delete-btn svg {
  width: 13px;
  height: 13px;
}

/* Quick questions */
.quick-questions {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.quick-btn {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.55rem 0.7rem;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text-secondary);
  font-size: 0.77rem;
  font-family: "Inter", sans-serif;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}
.quick-btn:hover:not(:disabled) {
  background: var(--color-accent-glow);
  border-color: var(--color-accent);
  color: var(--color-text-primary);
  transform: translateX(2px);
}
.quick-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.quick-btn-text {
  line-height: 1.3;
}

/* Feeds list */
.feeds-list {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  margin-bottom: 0.2rem;
}
.feed-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.74rem;
  color: var(--color-text-secondary);
}
.feed-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent-light);
  flex-shrink: 0;
}

/* Ingest button */
.ingest-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.58rem;
  background: var(--color-accent);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 0.8rem;
  font-weight: 600;
  font-family: "Inter", sans-serif;
  cursor: pointer;
  transition: opacity 0.2s ease;
}
.ingest-btn:hover:not(:disabled) {
  opacity: 0.9;
}
.ingest-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-icon {
  width: 14px;
  height: 14px;
}
.ingest-message {
  font-size: 0.74rem;
  margin: 0;
  padding: 0.4rem 0.5rem;
  border-radius: 6px;
}
.ingest-message.success {
  background: rgba(34, 197, 94, 0.1);
  color: #4ade80;
}
.ingest-message.error {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
}

/* Spinner */
.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 0.9rem;
  border-top: 1px solid var(--color-border);
}

/* Responsive (Off-canvas) */
@media (max-width: 768px) {
  .sidebar {
    position: absolute;
    top: 0;
    left: 0;
    transform: translateX(-100%);
    box-shadow: none;
  }
  .sidebar.is-open {
    transform: translateX(0);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3);
  }
}
</style>
