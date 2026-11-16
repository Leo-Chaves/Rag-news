<template>
  <transition name="fade">
    <div
      v-if="isOpen"
      :class="mode === 'screen' ? 'auth-screen' : 'modal-overlay'"
      @click.self="mode === 'modal' && $emit('close')"
    >
      <!-- Botão de tema no canto quando em modo tela cheia -->
      <button
        v-if="mode === 'screen'"
        type="button"
        class="screen-theme-btn"
        :title="isDarkMode ? 'Modo Claro' : 'Modo Escuro'"
        @click="$emit('toggle-theme')"
      >
        <svg v-if="!isDarkMode" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      </button>

      <div class="modal-content auth-modal" :class="{ 'screen-card': mode === 'screen' }">
        <div class="modal-header">
          <div class="brand-header-wrap">
            <div v-if="mode === 'screen'" class="brand-badge">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v2" />
                <path d="M2 20h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H2" />
                <path d="M6 10h8M6 14h8M6 18h4" />
              </svg>
            </div>
            <div class="modal-title-wrap">
              <h3>{{ user ? "Minha Conta Google" : "Entrar no RAG News" }}</h3>
              <span class="modal-sub">
                {{ user ? "Sessão autenticada via JWT" : "Login obrigatório · Google OAuth 2.0" }}
              </span>
            </div>
          </div>
          <button v-if="mode === 'modal'" class="close-btn" title="Fechar" @click="$emit('close')">
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
              Entre com sua conta Google para acessar o chat de notícias, salvar artigos, cadastrar fontes RSS ou tópicos personalizados e manter seu histórico de conversas.
            </p>

            <div class="google-actions-box">
              <!-- Botão principal sempre visível -->
              <button
                type="button"
                class="google-cta-btn"
                :disabled="isSubmitting || loadingConfig"
                @click="handleGoogleButtonClick"
              >
                <svg class="google-g-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="#4285F4"
                    d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24Z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14Z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96Z"
                  />
                </svg>
                <span>
                  {{
                    loadingConfig
                      ? "Carregando Google OAuth..."
                      : isSubmitting
                        ? "Conectando ao Google..."
                        : "Continuar com o Google"
                  }}
                </span>
              </button>

              <!-- Slot oficial GSI (acesso rápido / One Tap fallback) -->
              <div v-if="activeClientId" ref="googleBtnRef" class="gsi-slot" />
            </div>

            <!-- Campo simples exibido apenas quando o usuário clica sem GOOGLE_CLIENT_ID configurado -->
            <form v-if="showClientConfig" class="client-id-box" @submit.prevent="saveClientIdAndLogin">
              <label class="field-label">
                <span>Informe o Google Client ID para continuar</span>
                <input
                  v-model="clientIdDraft"
                  type="text"
                  required
                  class="text-input"
                  placeholder="seu-client-id.apps.googleusercontent.com"
                />
              </label>
              <button type="submit" class="primary-btn" :disabled="!clientIdDraft.trim() || isSubmitting">
                Confirmar e abrir Google
              </button>
            </form>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { authApi, usersApi } from "../services/api";

const GOOGLE_CLIENT_ID_KEY = "rag_news_google_client_id";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  mode: { type: String, default: "modal" }, // 'screen' | 'modal'
  user: { type: Object, default: null },
  notice: { type: String, default: "" },
  isDarkMode: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "authenticated", "updated-user", "logout", "toggle-theme"]);

const googleBtnRef = ref(null);
const loadingConfig = ref(false);
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

const profileName = ref("");
const profilePicture = ref("");

let gsiPollTimer = null;
let oneTapTriggeredForSession = false;

const userInitial = computed(() => {
  const source = props.user?.name || props.user?.email || "U";
  return source.trim().charAt(0).toUpperCase();
});

async function ensureClientIdLoaded() {
  if (activeClientId.value) return;
  loadingConfig.value = true;
  try {
    const config = await authApi.getConfig();
    const backendClientId = (config?.google_client_id || "").trim();
    if (backendClientId) {
      activeClientId.value = backendClientId;
      clientIdDraft.value = backendClientId;
    }
  } catch {
    // Caso o backend ainda não tenha GOOGLE_CLIENT_ID, o usuário poderá informar ao clicar no botão
  } finally {
    loadingConfig.value = false;
  }
}

async function syncStateOnOpen() {
  errorMsg.value = "";
  successMsg.value = "";

  if (!props.isOpen) {
    stopGsiPoll();
    return;
  }

  if (props.user) {
    profileName.value = props.user.name || "";
    profilePicture.value = props.user.picture_url || "";
    stopGsiPoll();
    return;
  }

  await ensureClientIdLoaded();
  if (activeClientId.value) {
    showClientConfig.value = false;
    await nextTick();
    initGoogleOneTapAndButton();
  }
}

onMounted(() => {
  if (props.isOpen) {
    syncStateOnOpen();
  }
});

watch(
  () => [props.isOpen, props.user, activeClientId.value],
  () => {
    syncStateOnOpen();
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

function setupGoogleIdServices() {
  if (!window.google?.accounts?.id || !activeClientId.value) {
    return false;
  }

  window.google.accounts.id.initialize({
    client_id: activeClientId.value,
    callback: handleGoogleCredentialResponse,
    auto_select: true,
  });

  if (googleBtnRef.value) {
    googleBtnRef.value.innerHTML = "";
    window.google.accounts.id.renderButton(googleBtnRef.value, {
      theme: props.isDarkMode ? "filled_black" : "outline",
      size: "medium",
      text: "continue_with",
      shape: "rectangular",
      width: 320,
    });
  }

  if (!oneTapTriggeredForSession) {
    oneTapTriggeredForSession = true;
    try {
      window.google.accounts.id.prompt();
    } catch {
      // Ignora caso o navegador bloqueie o One Tap automático
    }
  }

  return true;
}

function initGoogleOneTapAndButton() {
  stopGsiPoll();
  if (setupGoogleIdServices()) return;

  let attempts = 0;
  gsiPollTimer = setInterval(() => {
    attempts += 1;
    if (setupGoogleIdServices() || attempts > 30) {
      stopGsiPoll();
    }
  }, 200);
}

function waitForGoogleOAuth2(timeoutMs = 5000) {
  return new Promise((resolve) => {
    if (window.google?.accounts?.oauth2) {
      resolve(true);
      return;
    }
    const startedAt = Date.now();
    const timer = setInterval(() => {
      if (window.google?.accounts?.oauth2) {
        clearInterval(timer);
        resolve(true);
      } else if (Date.now() - startedAt >= timeoutMs) {
        clearInterval(timer);
        resolve(false);
      }
    }, 150);
  });
}

async function handleGoogleButtonClick() {
  errorMsg.value = "";
  if (!activeClientId.value) {
    await ensureClientIdLoaded();
  }

  if (!activeClientId.value) {
    showClientConfig.value = true;
    errorMsg.value =
      "Configure o GOOGLE_CLIENT_ID no backend/.env ou informe abaixo para abrir o login do Google.";
    return;
  }

  await openGoogleOAuthPopup();
}

async function openGoogleOAuthPopup() {
  isSubmitting.value = true;
  errorMsg.value = "";

  const loaded = await waitForGoogleOAuth2();
  if (!loaded) {
    isSubmitting.value = false;
    errorMsg.value =
      "Não foi possível carregar o script do Google Identity Services. Verifique sua conexão com a internet.";
    return;
  }

  try {
    const tokenClient = window.google.accounts.oauth2.initTokenClient({
      client_id: activeClientId.value,
      scope: "openid email profile",
      callback: async (tokenResponse) => {
        if (tokenResponse?.error || !tokenResponse?.access_token) {
          isSubmitting.value = false;
          errorMsg.value =
            tokenResponse?.error_description || "Autenticação com o Google não foi concluída.";
          return;
        }
        await performGoogleLogin(tokenResponse.access_token);
      },
      error_callback: () => {
        isSubmitting.value = false;
        errorMsg.value = "Janela de login do Google fechada ou bloqueada pelo navegador.";
      },
    });
    tokenClient.requestAccessToken({ prompt: "select_account" });
  } catch (err) {
    isSubmitting.value = false;
    errorMsg.value = err?.message || "Erro ao iniciar login com o Google.";
  }
}

async function saveClientIdAndLogin() {
  const clean = clientIdDraft.value.trim();
  if (!clean) return;
  activeClientId.value = clean;
  localStorage.setItem(GOOGLE_CLIENT_ID_KEY, clean);
  showClientConfig.value = false;
  oneTapTriggeredForSession = false;
  await nextTick();
  initGoogleOneTapAndButton();
  await openGoogleOAuthPopup();
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
    emit("authenticated", data);
  } catch (err) {
    errorMsg.value =
      err.response?.data?.detail || err.message || "Falha ao autenticar com o Google.";
  } finally {
    isSubmitting.value = false;
  }
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
  oneTapTriggeredForSession = false;
  emit("logout");
  emit("close");
}
</script>

<style scoped>
.auth-screen {
  min-height: 100dvh;
  width: 100%;
  background: var(--color-bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  position: relative;
}

.screen-theme-btn {
  position: fixed;
  top: 1rem;
  right: 1rem;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.screen-theme-btn:hover {
  color: var(--color-text-primary);
  border-color: var(--color-accent);
}
.screen-theme-btn svg {
  width: 18px;
  height: 18px;
}

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

.screen-card {
  max-width: 440px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.15rem 1.4rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.brand-header-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand-badge {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  background: var(--color-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-badge svg {
  width: 20px;
  height: 20px;
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
  margin: 0 0 1.1rem;
  font-size: 0.87rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.google-actions-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.85rem;
}

.google-cta-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.78rem 1.1rem;
  border-radius: 10px;
  border: 1px solid #dadce0;
  background: #ffffff;
  color: #1f1f1f;
  font-size: 0.92rem;
  font-weight: 600;
  font-family: "Inter", sans-serif;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: background 0.15s ease, transform 0.1s ease;
}

.google-cta-btn:hover:not(:disabled) {
  background: #f8f9fa;
}

.google-cta-btn:active:not(:disabled) {
  transform: scale(0.99);
}

.google-cta-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.google-g-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.gsi-slot {
  display: flex;
  justify-content: center;
  min-height: 0;
}

.client-id-box {
  margin-top: 0.75rem;
  padding: 0.9rem;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
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
