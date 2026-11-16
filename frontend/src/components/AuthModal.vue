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
              <h3>{{ user ? "Minha Conta" : isRegister ? "Criar Conta no RAG News" : "Entrar no RAG News" }}</h3>
              <span class="modal-sub">
                {{ user ? "Sessão autenticada via JWT" : "Acesse com seu e-mail e senha" }}
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

          <!-- Estado NÃO autenticado: Login / Cadastro -->
          <div v-if="!user" class="auth-login-flow">
            <div class="auth-tabs">
              <button
                type="button"
                class="auth-tab-btn"
                :class="{ active: !isRegister }"
                @click="switchMode(false)"
              >
                Entrar
              </button>
              <button
                type="button"
                class="auth-tab-btn"
                :class="{ active: isRegister }"
                @click="switchMode(true)"
              >
                Criar conta
              </button>
            </div>

            <form class="auth-form" @submit.prevent="submitAuth">
              <label v-if="isRegister" class="field-label">
                <span>Nome</span>
                <input
                  v-model="nameInput"
                  type="text"
                  class="text-input"
                  placeholder="Seu nome"
                  autocomplete="name"
                  :disabled="isSubmitting"
                />
              </label>

              <label class="field-label">
                <span>E-mail</span>
                <input
                  v-model="emailInput"
                  type="email"
                  required
                  class="text-input"
                  placeholder="voce@exemplo.com"
                  autocomplete="email"
                  :disabled="isSubmitting"
                />
              </label>

              <label class="field-label">
                <span>Senha</span>
                <div class="password-wrap">
                  <input
                    v-model="passwordInput"
                    :type="showPassword ? 'text' : 'password'"
                    required
                    :minlength="isRegister ? 6 : undefined"
                    class="text-input password-input"
                    :placeholder="isRegister ? 'Mínimo 6 caracteres' : 'Sua senha'"
                    :autocomplete="isRegister ? 'new-password' : 'current-password'"
                    :disabled="isSubmitting"
                  />
                  <button
                    type="button"
                    class="toggle-pw-btn"
                    tabindex="-1"
                    @click="showPassword = !showPassword"
                  >
                    {{ showPassword ? "Ocultar" : "Ver" }}
                  </button>
                </div>
              </label>

              <label v-if="isRegister" class="field-label">
                <span>Confirmar senha</span>
                <input
                  v-model="confirmPasswordInput"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  minlength="6"
                  class="text-input"
                  placeholder="Repita a senha"
                  autocomplete="new-password"
                  :disabled="isSubmitting"
                />
              </label>

              <button type="submit" class="primary-btn full-btn" :disabled="isSubmitting">
                {{
                  isSubmitting
                    ? "Aguarde..."
                    : isRegister
                      ? "Criar conta e entrar"
                      : "Entrar"
                }}
              </button>
            </form>
          </div>

          <!-- Estado AUTENTICADO: Perfil -->
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
                <strong>{{ user.name || "Usuário" }}</strong>
                <span>{{ user.email }}</span>
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
import { computed, ref, watch } from "vue";
import { authApi, usersApi } from "../services/api";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  mode: { type: String, default: "modal" }, // 'screen' | 'modal'
  user: { type: Object, default: null },
  notice: { type: String, default: "" },
  isDarkMode: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "authenticated", "updated-user", "logout", "toggle-theme"]);

const isRegister = ref(false);
const showPassword = ref(false);
const isSubmitting = ref(false);
const errorMsg = ref("");
const successMsg = ref("");

const nameInput = ref("");
const emailInput = ref("");
const passwordInput = ref("");
const confirmPasswordInput = ref("");

const profileName = ref("");
const profilePicture = ref("");

const userInitial = computed(() => {
  const source = props.user?.name || props.user?.email || "U";
  return source.trim().charAt(0).toUpperCase();
});

watch(
  () => [props.isOpen, props.user],
  ([open, currentUser]) => {
    errorMsg.value = "";
    successMsg.value = "";
    if (open && currentUser) {
      profileName.value = currentUser.name || "";
      profilePicture.value = currentUser.picture_url || "";
    }
  },
  { immediate: true }
);

function switchMode(registerMode) {
  isRegister.value = registerMode;
  errorMsg.value = "";
  successMsg.value = "";
  passwordInput.value = "";
  confirmPasswordInput.value = "";
}

async function submitAuth() {
  errorMsg.value = "";
  successMsg.value = "";

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (isRegister.value && password !== confirmPasswordInput.value) {
    errorMsg.value = "As senhas não coincidem.";
    return;
  }

  isSubmitting.value = true;
  try {
    const data = isRegister.value
      ? await authApi.register({
          name: nameInput.value.trim() || null,
          email,
          password,
        })
      : await authApi.login({ email, password });

    passwordInput.value = "";
    confirmPasswordInput.value = "";
    emit("authenticated", data);
  } catch (err) {
    const detail = err.response?.data?.detail;
    if (Array.isArray(detail)) {
      errorMsg.value = detail.map((item) => item.msg).join(" ");
    } else {
      errorMsg.value = detail || err.message || "Não foi possível autenticar.";
    }
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
  max-width: 440px;
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.35);
  overflow: hidden;
}

.screen-card {
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

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  padding: 0.25rem;
  border-radius: 10px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  margin-bottom: 1rem;
}

.auth-tab-btn {
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.auth-tab-btn.active {
  background: var(--color-accent);
  color: white;
}

.auth-form,
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

.text-input {
  width: 100%;
  padding: 0.58rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.85rem;
  font-family: "Inter", sans-serif;
  outline: none;
}

.text-input:focus {
  border-color: var(--color-accent);
}

.password-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input {
  padding-right: 4.2rem;
}

.toggle-pw-btn {
  position: absolute;
  right: 0.5rem;
  background: transparent;
  border: none;
  color: var(--color-accent-light);
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem 0.4rem;
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
  padding: 0.6rem 1rem;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
}

.full-btn {
  width: 100%;
  margin-top: 0.25rem;
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
