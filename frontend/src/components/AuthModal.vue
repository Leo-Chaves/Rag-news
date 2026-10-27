<template>
  <transition name="fade">
    <div v-if="open" class="modal-overlay" @click.self="close">
      <div class="modal-content" role="dialog" aria-modal="true" :aria-label="title">
        <div class="modal-header">
          <h3>{{ title }}</h3>
          <button class="close-btn" title="Fechar" @click="close">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        <!-- Abas entrar / criar conta -->
        <div v-if="mode === 'login' || mode === 'signup'" class="tabs">
          <button :class="{ active: mode === 'login' }" @click="switchMode('login')">Entrar</button>
          <button :class="{ active: mode === 'signup' }" @click="switchMode('signup')">Criar conta</button>
        </div>

        <form class="modal-body" @submit.prevent="submit">
          <p v-if="mode === 'forgot'" class="hint">
            Informe seu e-mail e enviaremos um link para você criar uma nova senha.
          </p>
          <p v-if="mode === 'reset'" class="hint">Digite sua nova senha.</p>

          <label v-if="mode === 'signup'" class="field">
            <span>Nome</span>
            <input v-model.trim="name" type="text" autocomplete="name" maxlength="60" required />
          </label>

          <label v-if="mode !== 'reset'" class="field">
            <span>E-mail</span>
            <input v-model.trim="email" type="email" autocomplete="email" required />
          </label>

          <label v-if="mode !== 'forgot'" class="field">
            <span>{{ mode === "reset" ? "Nova senha" : "Senha" }}</span>
            <input
              v-model="password"
              type="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              :minlength="mode === 'login' ? undefined : 8"
              required
            />
          </label>

          <button
            v-if="mode === 'login'"
            type="button"
            class="link-btn forgot"
            @click="switchMode('forgot')"
          >
            Esqueci minha senha
          </button>

          <p v-if="error" class="feedback error">{{ error }}</p>
          <p v-if="info" class="feedback success">{{ info }}</p>

          <button type="submit" class="primary-btn full" :disabled="busy">
            <span v-if="busy" class="spinner" />
            <span v-else>{{ submitLabel }}</span>
          </button>

          <template v-if="googleLoginEnabled && (mode === 'login' || mode === 'signup')">
            <div class="divider"><span>ou</span></div>
            <button type="button" class="secondary-btn full" :disabled="busy" @click="google">
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M21.35 11.1H12v2.98h5.35c-.23 1.5-1.68 4.4-5.35 4.4-3.22 0-5.85-2.67-5.85-5.96S8.78 6.56 12 6.56c1.83 0 3.06.78 3.76 1.45l2.56-2.47C16.68 4 14.55 3 12 3 6.98 3 2.9 7.03 2.9 12s4.08 9 9.1 9c5.25 0 8.73-3.69 8.73-8.89 0-.6-.07-1.05-.15-1.51z"/></svg>
              Continuar com Google
            </button>
          </template>

          <button v-if="mode === 'forgot'" type="button" class="link-btn" @click="switchMode('login')">
            ← Voltar para o login
          </button>
        </form>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { googleLoginEnabled } from "../lib/supabase";
import { useAuth } from "../composables/useAuth";

const props = defineProps({
  open: { type: Boolean, default: false },
  initialMode: { type: String, default: "login" }, // login | signup | forgot | reset
});
const emit = defineEmits(["close"]);

const { signIn, signUp, signInWithGoogle, sendPasswordReset, updatePassword } = useAuth();

const mode = ref(props.initialMode);
const name = ref("");
const email = ref("");
const password = ref("");
const busy = ref(false);
const error = ref("");
const info = ref("");

watch(
  () => [props.open, props.initialMode],
  ([open]) => {
    if (open) {
      mode.value = props.initialMode;
      password.value = "";
      error.value = "";
      info.value = "";
    }
  }
);

const title = computed(
  () =>
    ({
      login: "Entrar no RAG News",
      signup: "Criar sua conta",
      forgot: "Recuperar senha",
      reset: "Definir nova senha",
    })[mode.value]
);

const submitLabel = computed(
  () =>
    ({
      login: "Entrar",
      signup: "Criar conta",
      forgot: "Enviar link",
      reset: "Salvar nova senha",
    })[mode.value]
);

function switchMode(m) {
  mode.value = m;
  error.value = "";
  info.value = "";
}

function close() {
  if (!busy.value) emit("close");
}

async function submit() {
  busy.value = true;
  error.value = "";
  info.value = "";
  try {
    if (mode.value === "login") {
      await signIn(email.value, password.value);
      emit("close");
    } else if (mode.value === "signup") {
      const active = await signUp(name.value, email.value, password.value);
      if (active) {
        emit("close");
      } else {
        info.value = "Quase lá! Enviamos um link de confirmação para o seu e-mail.";
        password.value = "";
      }
    } else if (mode.value === "forgot") {
      await sendPasswordReset(email.value);
      // Mensagem neutra: não revela se o e-mail existe
      info.value = "Se houver uma conta com este e-mail, você receberá o link em instantes.";
    } else if (mode.value === "reset") {
      await updatePassword(password.value);
      info.value = "Senha alterada com sucesso!";
      setTimeout(() => emit("close"), 1200);
    }
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function google() {
  error.value = "";
  try {
    await signInWithGoogle(); // redireciona para o Google
  } catch (e) {
    error.value = e.message;
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
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
  max-width: 400px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.1rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}
.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
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

.tabs {
  display: flex;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}
.tabs button {
  flex: 1;
  padding: 0.7rem;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: 0.85rem;
  cursor: pointer;
}
.tabs button.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.5rem;
}
.hint {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.field input {
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 0.9rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
}
.field input:focus {
  border-color: var(--color-accent);
}

.link-btn {
  background: none;
  border: none;
  padding: 0;
  color: var(--color-accent);
  font-size: 0.8rem;
  cursor: pointer;
  align-self: flex-start;
}
.link-btn:hover {
  text-decoration: underline;
}
.link-btn.forgot {
  align-self: flex-end;
  margin-top: -0.4rem;
}

.feedback {
  margin: 0;
  font-size: 0.82rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  line-height: 1.45;
}
.feedback.error {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}
.feedback.success {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
  border: 1px solid rgba(22, 163, 74, 0.3);
}

.primary-btn,
.secondary-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 40px;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.88rem;
  cursor: pointer;
  transition: opacity 0.2s;
}
.primary-btn {
  background: var(--color-accent);
  color: white;
  border: none;
}
.secondary-btn {
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
}
.primary-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.full {
  width: 100%;
}

.divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
}
.divider::before,
.divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

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
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
