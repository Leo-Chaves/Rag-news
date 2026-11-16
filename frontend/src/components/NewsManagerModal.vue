<template>
  <transition name="fade">
    <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content news-modal">
        <!-- Header -->
        <div class="modal-header">
          <div>
            <h3>Central de Notícias & Acervo Pessoal</h3>
            <p class="modal-subtitle">
              Gerencie o feed global, notícias salvas e fontes RSS/artigos/tópicos personalizados
            </p>
          </div>
          <button class="close-btn" title="Fechar" @click="$emit('close')">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <!-- Tabs -->
        <div class="tabs-bar">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'feed' }"
            @click="switchTab('feed')"
          >
            🌐 Feed BBC
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'saved' }"
            @click="switchTab('saved')"
          >
            🔖 Salvas ({{ savedNews.length }})
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'sources' }"
            @click="switchTab('sources')"
          >
            📡 Fontes Personalizadas ({{ customSources.length }})
          </button>
        </div>

        <!-- Body -->
        <div class="modal-body">
          <div v-if="feedbackMsg" class="alert" :class="feedbackError ? 'error' : 'success'">
            {{ feedbackMsg }}
          </div>

          <!-- TAB 1: FEED GLOBAL BBC -->
          <div v-if="activeTab === 'feed'" class="tab-panel">
            <div class="panel-toolbar">
              <span class="toolbar-info">Manchetes recentes dos feeds RSS da BBC</span>
              <div class="toolbar-actions">
                <button class="secondary-btn" :disabled="loadingFeed" @click="loadGlobalFeed">
                  {{ loadingFeed ? "Carregando..." : "Recarregar Lista" }}
                </button>
                <button class="primary-btn" :disabled="ingestingGlobal" @click="handleIngestGlobal">
                  {{ ingestingGlobal ? "Indexando..." : "Ingerir BBC no RAG" }}
                </button>
              </div>
            </div>

            <div v-if="loadingFeed" class="empty-box">Buscando manchetes dos feeds RSS...</div>
            <div v-else-if="feedItems.length === 0" class="empty-box">
              Nenhuma notícia carregada no momento.
            </div>
            <div v-else class="cards-list">
              <article v-for="item in feedItems" :key="item.url" class="item-card">
                <div class="item-header">
                  <a :href="item.url" target="_blank" rel="noopener noreferrer" class="item-title">
                    {{ item.title }}
                  </a>
                  <span v-if="item.published_at" class="item-date">{{ item.published_at }}</span>
                </div>
                <p v-if="item.summary" class="item-summary">{{ item.summary }}</p>
                <div class="item-footer">
                  <a :href="item.url" target="_blank" rel="noopener noreferrer" class="item-link">
                    Abrir matéria ↗
                  </a>
                  <button
                    class="save-pill-btn"
                    :class="{ saved: isUrlSaved(item.url) }"
                    :disabled="isUrlSaved(item.url) || savingUrl === item.url"
                    @click="saveFromFeed(item)"
                  >
                    {{
                      isUrlSaved(item.url)
                        ? "✓ Salva na conta"
                        : savingUrl === item.url
                          ? "Salvando..."
                          : "🔖 Salvar na conta"
                    }}
                  </button>
                </div>
              </article>
            </div>
          </div>

          <!-- TAB 2: NOTÍCIAS SALVAS -->
          <div v-else-if="activeTab === 'saved'" class="tab-panel">
            <div v-if="!currentUser" class="auth-gate">
              <p>Entre com sua conta Google para salvar notícias e consultar seu acervo privado no chat.</p>
              <button class="primary-btn" @click="$emit('require-auth', 'Faça login com o Google para gerenciar suas notícias salvas.')">
                Entrar com Google
              </button>
            </div>

            <template v-else>
              <form class="add-box" @submit.prevent="handleSaveExternalUrl">
                <p class="add-box-title">Salvar notícia externa por URL</p>
                <div class="form-row">
                  <input
                    v-model="externalUrl"
                    type="url"
                    required
                    class="text-input"
                    placeholder="https://exemplo.com/noticia"
                    :disabled="savingExternal"
                  />
                  <input
                    v-model="externalTitle"
                    type="text"
                    class="text-input"
                    placeholder="Título (opcional — extraído automaticamente)"
                    :disabled="savingExternal"
                  />
                  <button type="submit" class="primary-btn" :disabled="!externalUrl.trim() || savingExternal">
                    {{ savingExternal ? "Indexando..." : "Salvar & Indexar" }}
                  </button>
                </div>
              </form>

              <div v-if="savedNews.length === 0" class="empty-box">
                Você ainda não salvou nenhuma notícia. Salve artigos do Feed BBC, de links externos ou das fontes citadas no chat.
              </div>
              <div v-else class="cards-list">
                <article v-for="news in savedNews" :key="news.id" class="item-card">
                  <div class="item-header">
                    <a :href="news.url" target="_blank" rel="noopener noreferrer" class="item-title">
                      {{ news.title }}
                    </a>
                    <div class="badges-row">
                      <span class="badge">{{ formatOrigin(news.origin) }}</span>
                      <span v-if="news.is_indexed" class="badge success">Indexada ✓</span>
                    </div>
                  </div>
                  <p v-if="news.summary" class="item-summary">{{ news.summary }}</p>
                  <div class="item-footer">
                    <button class="secondary-btn" @click="queryScope('saved', null)">
                      💬 Perguntar sobre Salvas
                    </button>
                    <button
                      class="danger-btn"
                      :disabled="deletingId === news.id"
                      @click="handleDeleteSaved(news.id)"
                    >
                      {{ deletingId === news.id ? "Removendo..." : "Excluir" }}
                    </button>
                  </div>
                </article>
              </div>
            </template>
          </div>

          <!-- TAB 3: FONTES PERSONALIZADAS -->
          <div v-else-if="activeTab === 'sources'" class="tab-panel">
            <div v-if="!currentUser" class="auth-gate">
              <p>Entre com sua conta Google para cadastrar feeds RSS, artigos diretos ou tópicos de interesse.</p>
              <button class="primary-btn" @click="$emit('require-auth', 'Faça login com o Google para gerenciar fontes personalizadas.')">
                Entrar com Google
              </button>
            </div>

            <template v-else>
              <form class="add-box" @submit.prevent="handleCreateSource">
                <p class="add-box-title">Adicionar nova fonte personalizada</p>
                <div class="source-form-grid">
                  <input
                    v-model="newSourceName"
                    type="text"
                    required
                    class="text-input"
                    placeholder="Nome (ex: TechCrunch, Artigo IA...)"
                    :disabled="creatingSource"
                  />
                  <select v-model="newSourceType" class="text-input" :disabled="creatingSource">
                    <option value="rss_feed">Feed RSS (URL)</option>
                    <option value="article_url">Artigo Direto (URL)</option>
                    <option value="topic">Tópico / Palavras-chave</option>
                  </select>
                  <input
                    v-if="newSourceType !== 'topic'"
                    v-model="newSourceUrl"
                    type="url"
                    required
                    class="text-input full-span"
                    :placeholder="newSourceType === 'rss_feed' ? 'https://site.com/rss.xml' : 'https://site.com/artigo'"
                    :disabled="creatingSource"
                  />
                  <input
                    v-else
                    v-model="newSourceKeywords"
                    type="text"
                    required
                    class="text-input full-span"
                    placeholder="Palavras-chave separadas por vírgula (ex: AI, OpenAI, climate)"
                    :disabled="creatingSource"
                  />
                </div>
                <div class="form-actions-end">
                  <button type="submit" class="primary-btn" :disabled="creatingSource">
                    {{ creatingSource ? "Adicionando..." : "+ Adicionar Fonte" }}
                  </button>
                </div>
              </form>

              <div v-if="customSources.length === 0" class="empty-box">
                Nenhuma fonte personalizada cadastrada. Adicione um feed RSS, URL de artigo ou tópico acima.
              </div>
              <div v-else class="cards-list">
                <article v-for="src in customSources" :key="src.id" class="item-card">
                  <div class="item-header">
                    <strong class="item-title">{{ src.name }}</strong>
                    <span class="badge">{{ formatSourceType(src.source_type) }}</span>
                  </div>
                  <p class="item-meta">
                    <span v-if="src.url">{{ src.url }}</span>
                    <span v-else-if="src.topic_keywords">Palavras-chave: {{ src.topic_keywords }}</span>
                  </p>
                  <p class="item-sync-info">
                    Última sincronização:
                    {{ src.last_synced_at ? formatDate(src.last_synced_at) : "Nunca sincronizada (clique em Sincronizar)" }}
                  </p>
                  <div class="item-footer">
                    <div class="footer-left">
                      <button
                        class="primary-btn small"
                        :disabled="syncingSourceId === src.id"
                        @click="handleSyncSource(src.id)"
                      >
                        {{ syncingSourceId === src.id ? "Sincronizando..." : "🔄 Sincronizar" }}
                      </button>
                      <button class="secondary-btn" @click="queryScope('custom', src.id)">
                        💬 Consultar esta fonte
                      </button>
                    </div>
                    <button
                      class="danger-btn"
                      :disabled="deletingId === src.id"
                      @click="handleDeleteSource(src.id)"
                    >
                      {{ deletingId === src.id ? "Removendo..." : "Excluir" }}
                    </button>
                  </div>
                </article>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from "vue";
import { newsApi } from "../services/api";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  initialTab: { type: String, default: "feed" },
  currentUser: { type: Object, default: null },
  savedNews: { type: Array, default: () => [] },
  customSources: { type: Array, default: () => [] },
});

const emit = defineEmits([
  "close",
  "require-auth",
  "refresh-saved",
  "refresh-sources",
  "global-ingested",
  "use-scope",
]);

const activeTab = ref("feed");
const feedbackMsg = ref("");
const feedbackError = ref(false);

const feedItems = ref([]);
const loadingFeed = ref(false);
const ingestingGlobal = ref(false);
const savingUrl = ref("");

const externalUrl = ref("");
const externalTitle = ref("");
const savingExternal = ref(false);

const newSourceName = ref("");
const newSourceType = ref("rss_feed");
const newSourceUrl = ref("");
const newSourceKeywords = ref("");
const creatingSource = ref(false);
const syncingSourceId = ref(null);
const deletingId = ref(null);

watch(
  () => [props.isOpen, props.initialTab],
  ([open, tab]) => {
    if (open) {
      activeTab.value = tab || "feed";
      feedbackMsg.value = "";
      feedbackError.value = false;
      if (activeTab.value === "feed" && feedItems.value.length === 0) {
        loadGlobalFeed();
      }
    }
  }
);

function switchTab(tab) {
  activeTab.value = tab;
  feedbackMsg.value = "";
  if (tab === "feed" && feedItems.value.length === 0) {
    loadGlobalFeed();
  }
}

function setFeedback(msg, isError = false) {
  feedbackMsg.value = msg;
  feedbackError.value = isError;
}

function isUrlSaved(url) {
  return props.savedNews.some((item) => item.url === url);
}

async function loadGlobalFeed() {
  loadingFeed.value = true;
  try {
    feedItems.value = await newsApi.getGlobalFeed(30);
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao carregar feed da BBC.", true);
  } finally {
    loadingFeed.value = false;
  }
}

async function handleIngestGlobal() {
  ingestingGlobal.value = true;
  setFeedback("");
  try {
    const data = await newsApi.ingestGlobalFeed();
    const msg =
      data.chunks_stored === 0 && data.skipped > 0
        ? `Notícias globais já estão atualizadas (${data.skipped} já existiam).`
        : `${data.chunks_stored} chunks de ${data.articles_processed} artigos indexados no PGVector.`;
    setFeedback(msg, false);
    emit("global-ingested", msg);
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao ingerir feeds da BBC.", true);
  } finally {
    ingestingGlobal.value = false;
  }
}

async function saveFromFeed(item) {
  if (!props.currentUser) {
    emit("require-auth", "Faça login com o Google para salvar notícias na sua conta.");
    return;
  }
  savingUrl.value = item.url;
  setFeedback("");
  try {
    await newsApi.saveNews({
      url: item.url,
      title: item.title,
      summary: item.summary,
      published_at: item.published_at || null,
      origin: "global_feed",
    });
    setFeedback(`Notícia "${item.title}" salva e indexada no seu acervo!`, false);
    emit("refresh-saved");
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao salvar notícia.", true);
  } finally {
    savingUrl.value = "";
  }
}

async function handleSaveExternalUrl() {
  if (!externalUrl.value.trim()) return;
  savingExternal.value = true;
  setFeedback("");
  try {
    const saved = await newsApi.saveNews({
      url: externalUrl.value.trim(),
      title: externalTitle.value.trim() || null,
      origin: "external_url",
    });
    externalUrl.value = "";
    externalTitle.value = "";
    setFeedback(`Notícia "${saved.title}" salva e indexada!`, false);
    emit("refresh-saved");
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao extrair ou salvar notícia.", true);
  } finally {
    savingExternal.value = false;
  }
}

async function handleDeleteSaved(newsId) {
  deletingId.value = newsId;
  setFeedback("");
  try {
    await newsApi.deleteSavedNews(newsId);
    setFeedback("Notícia removida da sua conta e do índice vetorial.", false);
    emit("refresh-saved");
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao remover notícia.", true);
  } finally {
    deletingId.value = null;
  }
}

async function handleCreateSource() {
  creatingSource.value = true;
  setFeedback("");
  try {
    const payload = {
      name: newSourceName.value.trim(),
      source_type: newSourceType.value,
      url: newSourceType.value !== "topic" ? newSourceUrl.value.trim() : null,
      topic_keywords: newSourceType.value === "topic" ? newSourceKeywords.value.trim() : null,
    };
    const created = await newsApi.createCustomSource(payload);
    newSourceName.value = "";
    newSourceUrl.value = "";
    newSourceKeywords.value = "";
    setFeedback(
      `Fonte "${created.name}" cadastrada! Clique em "Sincronizar" para indexar seus conteúdos.`,
      false
    );
    emit("refresh-sources");
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao cadastrar fonte personalizada.", true);
  } finally {
    creatingSource.value = false;
  }
}

async function handleSyncSource(sourceId) {
  syncingSourceId.value = sourceId;
  setFeedback("");
  try {
    const res = await newsApi.syncCustomSource(sourceId);
    setFeedback(
      `${res.message} (${res.articles_processed} artigos, ${res.chunks_stored} chunks indexados, ${res.skipped} já existentes).`,
      false
    );
    emit("refresh-sources");
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao sincronizar fonte personalizada.", true);
  } finally {
    syncingSourceId.value = null;
  }
}

async function handleDeleteSource(sourceId) {
  deletingId.value = sourceId;
  setFeedback("");
  try {
    await newsApi.deleteCustomSource(sourceId);
    setFeedback("Fonte personalizada e vetores associados removidos.", false);
    emit("refresh-sources");
  } catch (err) {
    setFeedback(err.response?.data?.detail || "Erro ao remover fonte.", true);
  } finally {
    deletingId.value = null;
  }
}

function queryScope(scope, customSourceId) {
  emit("use-scope", { scope, customSourceId });
  emit("close");
}

function formatOrigin(origin) {
  const map = {
    global_feed: "Feed Global",
    external_url: "Link Externo",
    custom_source: "Fonte Personalizada",
  };
  return map[origin] || origin;
}

function formatSourceType(type) {
  const map = {
    rss_feed: "Feed RSS",
    article_url: "Artigo Direto",
    topic: "Tópico",
  };
  return map[type] || type;
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR");
  } catch {
    return iso;
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 110;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.news-modal {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  width: 100%;
  max-width: 820px;
  max-height: 88dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.1rem 1.4rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--color-text-primary);
}

.modal-subtitle {
  margin: 0.2rem 0 0;
  font-size: 0.76rem;
  color: var(--color-text-muted);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  padding: 0.25rem;
}

.close-btn:hover {
  color: var(--color-text-primary);
}

.tabs-bar {
  display: flex;
  gap: 0.35rem;
  padding: 0.65rem 1.4rem 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  overflow-x: auto;
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.6rem 0.9rem;
  color: var(--color-text-secondary);
  font-size: 0.84rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.tab-btn.active {
  color: var(--color-accent-light);
  border-bottom-color: var(--color-accent);
  font-weight: 600;
}

.modal-body {
  padding: 1.25rem 1.4rem;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.toolbar-info {
  font-size: 0.82rem;
  color: var(--color-text-secondary);
}

.toolbar-actions {
  display: flex;
  gap: 0.5rem;
}

.alert {
  padding: 0.65rem 0.9rem;
  border-radius: 8px;
  font-size: 0.82rem;
}

.alert.success {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  color: #4ade80;
}

.alert.error {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #f87171;
}

.auth-gate,
.empty-box {
  padding: 2rem 1rem;
  text-align: center;
  border: 1px dashed var(--color-border);
  border-radius: 10px;
  color: var(--color-text-secondary);
  font-size: 0.86rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.85rem;
}

.add-box {
  padding: 1rem;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.add-box-title {
  margin: 0;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.form-row {
  display: grid;
  grid-template-columns: 1.4fr 1.2fr auto;
  gap: 0.55rem;
}

.source-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.55rem;
}

.full-span {
  grid-column: 1 / -1;
}

.form-actions-end {
  display: flex;
  justify-content: flex-end;
}

.text-input {
  width: 100%;
  padding: 0.52rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.83rem;
  font-family: "Inter", sans-serif;
  outline: none;
}

.text-input:focus {
  border-color: var(--color-accent);
}

.cards-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.item-card {
  padding: 0.95rem;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.item-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-primary);
  text-decoration: none;
  line-height: 1.35;
}

a.item-title:hover {
  color: var(--color-accent-light);
  text-decoration: underline;
}

.item-date {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.item-summary {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-meta,
.item-sync-info {
  margin: 0;
  font-size: 0.77rem;
  color: var(--color-text-muted);
  word-break: break-all;
}

.badges-row {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}

.badge {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 99px;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  background: var(--color-bg-primary);
  white-space: nowrap;
}

.badge.success {
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.35);
}

.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
  flex-wrap: wrap;
}

.footer-left {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.item-link {
  font-size: 0.78rem;
  color: var(--color-accent-light);
  text-decoration: none;
}

.item-link:hover {
  text-decoration: underline;
}

.primary-btn {
  background: var(--color-accent);
  color: white;
  border: none;
  padding: 0.52rem 0.9rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.primary-btn.small {
  padding: 0.4rem 0.75rem;
  font-size: 0.78rem;
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-btn,
.save-pill-btn {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  font-size: 0.78rem;
  cursor: pointer;
  white-space: nowrap;
}

.save-pill-btn.saved {
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.4);
  cursor: default;
}

.danger-btn {
  background: transparent;
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.35);
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  font-size: 0.78rem;
  cursor: pointer;
}

.danger-btn:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.1);
}

@media (max-width: 640px) {
  .form-row,
  .source-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

