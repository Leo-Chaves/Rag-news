<template>
  <transition name="fade">
    <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content auth-modal">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <h3>{{ user ? "Minha Conta Google" : "Entrar no RAG News" }}</h3>
            <span class="modal-sub">
              {{ user ? "Sessão autenticada via JWT" : "Autenticação exclusiva com Google OAuth 2.0" }}
            </span>
          </div>
          <button class="close-btn" title="Fechar" @click="$emit('close')">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <div v-if="notice && !user" class="notice-banner">
            {{ notice }}
          </div>

          <div v-if="errorMsg" class="alert error">
            {{ errorMsg }}
          </div>
          <div v-if="successMsg" class="alert success">
            {{ successMsg }}
          </div>

          <!-- Estado NÃO autenticado -->
          <div v-if="!user" class="auth-login-flow">
            <p class="auth-description">
              Entre com sua conta Google para salvar notícias, cadastrar feeds RSS ou tópicos personalizados e consultar seu acervo privado no chat RAG.
            </p>

            <!-- Botão oficial Google Identity Services -->
            <div class="gsi-box">
              <div v-if="activeClientId" class="gsi-btn-holder">
                <div ref="googleBtnRef" class="gsi-target" />
                <p v-if="!gsiReady" class="muted-hint">Carregando botão do Google...</p>
              </div>
              <div v-else class="client-id-missing">
                <p class="muted-hint">
                  Nenhum <code>VITE_GOOGLE_CLIENT_ID</code> configurado. Informe um Client ID OAuth 2.0 abaixo para usar o botão do Google ou use o login com token manual.
                </p>
              </div>

              <div class="client-id-config">
                <button type="button" class="link-toggle" @click="showClientConfig = !showClientConfig">
                  {{ showClientConfig ? "Ocultar Client ID" : (activeClientId ? "Alterar Google Client ID" : "Configurar Google Client ID") }}
                </button>
                <div v-if="showClientConfig" class="inline-form">
                  <input
                    v-model="clientIdDraft"
                    type="text"
                    class="text-input"
                    placeholder="xxxx.apps.googleusercontent.com"
                  />
                  <button type="button" class="secondary-btn" @click="saveClientId">
                    Aplicar
                  </button>
                </div>
              </div>
            </div>

            <!-- Fallback para testes com token manual -->
            <div class="dev-token-section">
              <button type="button" class="link-toggle" @click="showManualToken = !showManualToken">
                {{ showManualToken ? "▾ Ocultar login com token manual" : "▸ Modo desenvolvedor: colar Google ID/Access Token" }}
              </button>
              <form v-if="showManualToken" class="manual-form" @submit.prevent="submitManualToken">
                <textarea
                  v-model="manualToken"
                  rows="3"
                  class="text-input"
                  placeholder="Cole aqui um Google id_token (JWT) ou access_token..."
                  :disabled="isSubmitting"
                />
                <button type="submit" class="primary-btn" :disabled="!manualToken.trim() || isSubmitting">
                  {{ isSubmitting ? "Autenticando..." : "Autenticar com Token" }}
                </button>
              </form>
            </div>
          </div>

          <!-- Estado AUTENTICADO -->
          <div v-else class="profile-flow">
            <div class="profile-card">
              <img
                v-if="user.picture_url"
                :src="user.picture_url"
                :alt="user.name || user.email"
                class="profile-avatar"
                referrerpolicy="no-referrer"
              />
              <div v-else class="profile-avatar-fallback">
                {{ userInitial }}
              </div>
              <div class="profile-meta">
                <strong>{{ user.name || "Usuário Google" }}</strong>
                <span>{{ user.email }}</span>
                <small>Google ID: {{ user.google_sub }}</small>
              </div>
            </div>

            <form class="profile-form" @submit.prevent="saveProfile">
              <label class="field-label">
                <span>Nome de exibição</span>
                <input v-model="profileName" type="text" class="text-input" placeholder="Seu nome" />
              </label>
              <label class="field-label">
                <span>URL da foto (opcional)</span>
                <input v-model="profilePicture" type="url" class="text-input" placeholder="https://..." />
              </label>

              <div class="profile-actions">
                <button type="button" class="danger-outline-btn" @click="handleLogout">
                  Sair da conta
                </button>
                <button type="submit" class="primary-btn" :disabled="isSubmitting">
                  {{ isSubmitting ? "Salvando..." : "Salvar perfil" }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { authApi, usersApi } from "../services/api";

const GOOGLE_CLIENT_ID_KEY = "rag_news_google_client_id";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  user: { type: Object, default: null },
  notice: { type: String, default: "" },
});

const emit = defineEmits(["close", "authenticated", "updated-user", "logout"]);

const googleBtnRef = ref(null);
const gsiReady = ref(false);
const isSubmitting = ref(false);
const errorMsg = ref("");
const successMsg = ref("");

const activeClientId = ref(
  (import.meta.env.VITE_GOOGLE_CLIENT_ID || "").trim() ||
    localStorage.getItem(GOOGLE_CLIENT_ID_KEY) ||
    ""
);
const clientIdDraft = ref(activeClientId.value);
const showClientConfig = ref(false);

const showManualToken = ref(false);
const manualToken = ref("");

const profileName = ref("");
const profilePicture = ref("");

let gsiPollTimer = null;

const userInitial = computed(() => {
  const source = props.user?.name || props.user?.email || "U";
  return source.trim().charAt(0).toUpperCase();
});

watch(
  () => [props.isOpen, props.user, activeClientId.value],
  async ([open, currentUser]) => {
    errorMsg.value = "";
    successMsg.value = "";

    if (!open) {
      stopGsiPoll();
      return;
    }

    if (currentUser) {
      profileName.value = currentUser.name || "";
      profilePicture.value = currentUser.picture_url || "";
      stopGsiPoll();
    } else if (activeClientId.value) {
      await nextTick();
      initGoogleButton();
    }
  }
);

onBeforeUnmount(() => {
  stopGsiPoll();
});

function stopGsiPoll() {
  if (gsiPollTimer) {
    clearInterval(gsiPollTimer);
    gsiPollTimer = null;
  }
}

function renderGsiButton() {
  if (!window.google?.accounts?.id || !googleBtnRef.value || !activeClientId.value) {
    return false;
  }
  googleBtnRef.value.innerHTML = "";
  window.google.accounts.id.initialize({
    client_id: activeClientId.value,
    callback: handleGoogleCredentialResponse,
  });
  window.google.accounts.id.renderButton(googleBtnRef.value, {
    theme: "outline",
    size: "large",
    text: "continue_with",
    shape: "rectangular",
    width: 320,
  });
  gsiReady.value = true;
  return true;
}

function initGoogleButton() {
  stopGsiPoll();
  gsiReady.value = false;
  if (renderGsiButton()) return;

  let attempts = 0;
  gsiPollTimer = setInterval(() => {
    attempts += 1;
    if (renderGsiButton() || attempts > 30) {
      stopGsiPoll();
    }
  }, 200);
}

async function handleGoogleCredentialResponse(response) {
  if (!response?.credential) {
    errorMsg.value = "O Google não retornou uma credencial válida.";
    return;
  }
  await performGoogleLogin(response.credential);
}

async function performGoogleLogin(token) {
  isSubmitting.value = true;
  errorMsg.value = "";
  successMsg.value = "";
  try {
    const data = await authApi.loginWithGoogle(token);
    manualToken.value = "";
    emit("authenticated", data);
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || err.message || "Falha ao autenticar com o Google.";
  } finally {
    isSubmitting.value = false;
  }
}

function saveClientId() {
  const clean = clientIdDraft.value.trim();
  activeClientId.value = clean;
  if (clean) {
    localStorage.setItem(GOOGLE_CLIENT_ID_KEY, clean);
    nextTick(() => initGoogleButton());
  } else {
    localStorage.removeItem(GOOGLE_CLIENT_ID_KEY);
    gsiReady.value = false;
  }
}

async function submitManualToken() {
  if (!manualToken.value.trim()) return;
  await performGoogleLogin(manualToken.value.trim());
}

async function saveProfile() {
  isSubmitting.value = true;
  errorMsg.value = "";
  successMsg.value = "";
  try {
    const updated = await usersApi.updateProfile({
      name: profileName.value.trim() || null,
      picture_url: profilePicture.value.trim() || null,
    });
    successMsg.value = "Perfil atualizado com sucesso.";
    emit("updated-user", updated);
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || "Não foi possível atualizar o perfil.";
  } finally {
    isSubmitting.value = false;
  }
}

function handleLogout() {
  emit("logout");
  emit("close");
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.auth-modal {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  width: 100%;
  max-width: 460px;
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.15rem 1.4rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.modal-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--color-text-primary);
}

.modal-sub {
  font-size: 0.74rem;
  color: var(--color-text-muted);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  padding: 0.25rem;
  border-radius: 6px;
}

.close-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
}

.modal-body {
  padding: 1.35rem 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.notice-banner {
  padding: 0.7rem 0.9rem;
  border-radius: 8px;
  background: rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.35);
  color: var(--color-text-primary);
  font-size: 0.82rem;
  line-height: 1.45;
}

.alert {
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  font-size: 0.82rem;
}

.alert.error {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #f87171;
}

.alert.success {
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  color: #4ade80;
}

.auth-description {
  margin: 0 0 1rem;
  font-size: 0.87rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.gsi-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px dashed var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-secondary);
}

.gsi-btn-holder {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 44px;
}

.muted-hint {
  margin: 0;
  font-size: 0.76rem;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.45;
}

.client-id-config {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.link-toggle {
  background: transparent;
  border: none;
  color: var(--color-accent-light);
  font-size: 0.76rem;
  cursor: pointer;
  padding: 0.15rem 0;
  text-align: left;
}

.link-toggle:hover {
  text-decoration: underline;
}

.inline-form {
  display: flex;
  gap: 0.45rem;
  width: 100%;
}

.dev-token-section {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.manual-form {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.text-input {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.84rem;
  font-family: "Inter", sans-serif;
  outline: none;
}

.text-input:focus {
  border-color: var(--color-accent);
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.85rem;
  border-radius: 10px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
}

.profile-avatar,
.profile-avatar-fallback {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.profile-avatar-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-accent);
  color: white;
  font-weight: 700;
  font-size: 1.15rem;
}

.profile-meta {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.profile-meta strong {
  font-size: 0.92rem;
  color: var(--color-text-primary);
}

.profile-meta span {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
}

.profile-meta small {
  font-size: 0.68rem;
  color: var(--color-text-muted);
}

.profile-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.field-label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.78rem;
  color: var(--color-text-secondary);
}

.profile-actions {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.primary-btn {
  background: var(--color-accent);
  color: white;
  border: none;
  padding: 0.55rem 1rem;
  border-radius: 8px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-btn {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  padding: 0.5rem 0.85rem;
  border-radius: 8px;
  font-size: 0.8rem;
  cursor: pointer;
  white-space: nowrap;
}

.danger-outline-btn {
  background: transparent;
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.4);
  padding: 0.55rem 0.95rem;
  border-radius: 8px;
  font-size: 0.82rem;
  cursor: pointer;
}

.danger-outline-btn:hover {
  background: rgba(239, 68, 68, 0.1);
}
</style>
